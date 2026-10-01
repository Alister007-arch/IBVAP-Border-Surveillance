"""
backend/engine.py
-----------------
Core Multi-Camera Pipeline Engine for IBVAP.

Orchestrates the entire surveillance pipeline across all active cameras:
  Camera Source -> Night/Day Auto-Switch -> Tier 1+3 Detection ->
  Merger -> Within-Camera Tracker -> Cross-Camera Re-ID ->
  6-Tier Tactical Coordinator (FRS, ANPR, Virtual Fence, Suspicious Activity) ->
  Visualizer -> WebSocket Broadcast.
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import logging
import math
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Enable 1ms high-precision multimedia timer on Windows for 150+ FPS pacing
if sys.platform.startswith("win"):
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass

import cv2
import numpy as np

from backend.alerts.schema import Alert, AlertPriority, AlertCategory
from backend.alerts.section_coordinator import SectionCoordinator
from backend.config.settings import settings
from backend.detection.merger import merge_detections
from backend.detection.night_switch import NightSwitcher
from backend.detection.tier1_yolo import Tier1Detector
from backend.detection.tier2_sahi import Tier2SAHIDetector
from backend.detection.tier3_motion import Tier3MotionDetector
from backend.detection.visualizer import draw_detections, encode_jpeg
from backend.ingestion.frame_model import Detection, Frame
from backend.ingestion.video_source import (
    BaseVideoSource,
    IPCCTVSource,
    VideoFileSource,
    WebcamSource,
    source_from_config,
)
from backend.reid.matcher import CrossCameraReIDMatcher
from backend.tracking.tracker import WithinCameraTracker

logger = logging.getLogger("SurveillanceEngine")
REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "camera_registry.json"


class CameraPipelineWorker:
    """
    Worker running an async processing loop for one camera feed.
    Features decoupled asynchronous AI inference to sustain up to 150 FPS.
    """

    def __init__(
        self,
        camera_cfg: dict,
        detector_t1: Tier1Detector,
        reid_matcher: CrossCameraReIDMatcher,
        broadcast_frame_cb,
        broadcast_alert_cb,
        detector_t2: Optional[Tier2SAHIDetector] = None,
    ):
        self.camera_cfg = camera_cfg
        self.camera_id = camera_cfg["camera_id"]
        self.location = camera_cfg.get("location", self.camera_id)
        self.boundary_line = camera_cfg.get("boundary_line") or camera_cfg.get("boundary", ((0, 240), (854, 240)))
        self.perimeter_polygon = camera_cfg.get("perimeter_polygon", None)

        self.detector_t1 = detector_t1
        self.detector_t2 = detector_t2 or (Tier2SAHIDetector(model=detector_t1._model) if detector_t1 else None)
        self.reid_matcher = reid_matcher
        self.broadcast_frame_cb = broadcast_frame_cb
        self.broadcast_alert_cb = broadcast_alert_cb

        # Per-camera modules
        self.night_switcher = NightSwitcher(self.camera_id)
        self.motion_detector = Tier3MotionDetector(self.camera_id)
        self.tracker = WithinCameraTracker(self.camera_id)
        self.coordinator = SectionCoordinator(
            camera_id=self.camera_id,
            location=self.location,
            reid_matcher=self.reid_matcher,
            boundary_line=self.boundary_line,
            perimeter_polygon=self.perimeter_polygon,
        )

        # State tracking
        self.is_running = False
        self.known_active_tracks: Set[int] = set()
        self.track_global_map: Dict[int, str] = {}
        self.last_known_positions: Dict[int, dict] = {}
        self.frame_count = 0
        self.cached_t1_dets: List[Detection] = []
        self.current_fps: float = 0.0
        self._fps_window: List[float] = []
        self.task: Optional[asyncio.Task] = None

        # Decoupled Async Inference State for up to 250 FPS streaming
        self._async_inference = getattr(settings.pipeline, "async_inference", True)
        self._latest_raw_frame: Optional[Frame] = None
        self._cached_merged_dets: List[Detection] = []
        self._cached_tracked_dets: List[Detection] = []
        self._cached_is_night: bool = False
        self._has_new_dets: bool = False
        self._pending_bg_alerts: List[Alert] = []
        self._frame_event: asyncio.Event = asyncio.Event()
        self._state_lock: threading.Lock = threading.Lock()
        self._inference_task: Optional[asyncio.Task] = None

        # Threaded Ingestion & Decoupled Non-Blocking IO
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader_ev: threading.Event = threading.Event()
        self._frame_in_queue: queue.Queue[Frame] = queue.Queue(maxsize=2)
        self._source_instance: Optional[BaseVideoSource] = None
        self._smooth_boxes: Dict[int, Tuple[float, float, float, float]] = {}

    def _smooth_detection_box(self, det: Detection) -> None:
        """
        Velocity-adaptive box smoothing:
        - When running/sprinting (speed > 8 px/frame): high responsiveness (alpha=0.92) to eliminate lagging.
        - When stationary/slow: gentle smoothing (alpha=0.65) to eliminate pixel jitter.
        """
        tid = det.track_id
        if tid is None:
            return
        b = det.bbox
        vx, vy = 0.0, 0.0
        if hasattr(self, "tracker") and hasattr(self.tracker, "get_track_velocity"):
            vx, vy = self.tracker.get_track_velocity(tid)
        speed = math.hypot(vx, vy)
        alpha = 0.92 if speed > 8.0 else 0.65

        if tid in self._smooth_boxes:
            old = self._smooth_boxes[tid]
            if abs(b[0] - old[0]) < 260 and abs(b[1] - old[1]) < 260:
                smoothed = (
                    round(alpha * b[0] + (1.0 - alpha) * old[0], 1),
                    round(alpha * b[1] + (1.0 - alpha) * old[1], 1),
                    round(alpha * b[2] + (1.0 - alpha) * old[2], 1),
                    round(alpha * b[3] + (1.0 - alpha) * old[3], 1),
                )
                det.bbox = smoothed
        self._smooth_boxes[tid] = det.bbox

    def _run_heavy_inference_pass(
        self, frame: Frame
    ) -> Tuple[List[Detection], bool, List[Alert]]:
        """
        Runs heavy AI detection models (YOLOv12, MOG2, SAHI) in a worker thread.
        This runs decoupled from the high-rate 150 FPS rendering and streaming loop.
        """
        # 1. Night/Day auto-switch & preprocessing
        proc_frame, is_night, avg_lum = self.night_switcher.process(frame)

        # 2. Tier-1 Detection (YOLOv12)
        conf_thresh = (
            settings.detection.night_confidence
            if is_night
            else settings.detection.day_confidence
        )
        t1_dets = self.detector_t1.detect(proc_frame, confidence=conf_thresh)

        # 3. Tier-3 Motion Catch-all (Adaptive MOG2 Fallback)
        t3_dets = self.motion_detector.detect(proc_frame)

        # 4. Tier-2 Sliced Airspace Detection (Motion-Gated SAHI for Drones / Small Air Threats)
        # ONLY trigger SAHI when there is genuinely small high-altitude motion in the upper sky (top 38% and blob < 120px)
        h_sky = proc_frame.shape[0] * 0.38
        has_airspace_motion = any(
            d.bbox[1] < h_sky and (d.bbox[2] - d.bbox[0]) < 120 and (d.bbox[3] - d.bbox[1]) < 120
            for d in t3_dets
        )
        t2_dets = (
            self.detector_t2.detect(
                proc_frame,
                confidence=conf_thresh,
                has_airspace_motion=has_airspace_motion,
            )
            if self.detector_t2
            else []
        )

        # 5. Merge tiers
        merged_dets = merge_detections(t1_dets, t2_dets, t3_dets)

        return merged_dets, is_night, []

    async def _run_inference_loop(self):
        """
        Dedicated background worker for heavy AI model inferences:
        YOLOv12 Tier 1, MOG2 Tier 3, Motion-Gated SAHI Tier 2.
        Runs continuously and asynchronously updates self._cached_merged_dets,
        allowing the main streaming loop to hit up to 150 FPS without stutter.
        """
        logger.info("[%s] Decoupled async inference loop active (YOLOv12 background worker)", self.camera_id)
        while self.is_running:
            try:
                await self._frame_event.wait()
                self._frame_event.clear()

                with self._state_lock:
                    frame = self._latest_raw_frame

                if frame is None or not self.is_running:
                    continue

                merged_dets, is_night, bg_alerts = await asyncio.to_thread(
                    self._run_heavy_inference_pass, frame
                )

                with self._state_lock:
                    self._cached_merged_dets = merged_dets
                    self._cached_is_night = is_night
                    self._has_new_dets = True
                    if bg_alerts:
                        self._pending_bg_alerts.extend(bg_alerts)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[%s] Async inference loop error: %s", self.camera_id, exc)
                await asyncio.sleep(0.01)

    def _process_single_frame(self, frame: Frame) -> Tuple[np.ndarray, List[Alert]]:
        """
        Synchronous processing of a single video frame with IBVAP AI suite.
        Optimized for high-FPS throughput using YOLOv12 and motion-gated SAHI.
        """
        self.frame_count += 1

        # 1. Night/Day auto-switch & preprocessing
        proc_frame, is_night, avg_lum = self.night_switcher.process(frame)

        # 2. Tier-1 Detection (YOLOv12 with detection stride)
        conf_thresh = (
            settings.detection.night_confidence
            if is_night
            else settings.detection.day_confidence
        )
        stride = max(1, getattr(settings.detection, "detection_stride", 1))
        should_detect_t1 = (self.frame_count % stride == 0) or not self.cached_t1_dets

        if should_detect_t1:
            t1_dets = self.detector_t1.detect(proc_frame, confidence=conf_thresh)
            self.cached_t1_dets = t1_dets
        else:
            t1_dets = self.cached_t1_dets

        # 3. Tier-3 Motion Catch-all (Adaptive MOG2 Fallback)
        t3_dets = self.motion_detector.detect(proc_frame)

        # 2.1 Tier-2 Sliced Airspace Detection (Motion-Gated SAHI for Drones / Small Air Threats)
        has_airspace_motion = any(d.bbox[1] < (proc_frame.shape[0] * 0.65) for d in t3_dets)
        t2_dets = self.detector_t2.detect(
            proc_frame,
            confidence=conf_thresh,
            has_airspace_motion=has_airspace_motion,
        ) if self.detector_t2 else []

        # 4. Merge tiers
        merged_dets = merge_detections(t1_dets, t2_dets, t3_dets)

        # 5. Within-Camera Tracking
        tracked_dets = self.tracker.update(merged_dets, proc_frame.shape)

        # 6. Re-ID Global ID assignment
        current_track_ids = set()
        for det in tracked_dets:
            if det.track_id is not None:
                current_track_ids.add(det.track_id)
                if det.track_id not in self.track_global_map:
                    x1, y1, x2, y2 = [int(v) for v in det.bbox]
                    crop = proc_frame.img[max(0, y1):min(proc_frame.shape[0], y2), max(0, x1):min(proc_frame.shape[1], x2)]
                    if crop.size > 0:
                        hist = cv2.calcHist([crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                        emb = cv2.normalize(hist, hist).flatten()
                        matched_gid = self.reid_matcher.match(self.camera_id, emb)
                        if not matched_gid:
                            matched_gid = self.reid_matcher._next_global_id()
                        self.track_global_map[det.track_id] = matched_gid
                        self.reid_matcher.register_exit(self.camera_id, det.track_id, emb, matched_gid)

                det.global_id = self.track_global_map.get(det.track_id)

        self.known_active_tracks = current_track_ids

        # 7. Comprehensive Tactical Coordinator Analysis:
        # (FRS, ANPR, Virtual Fence, Suspicious Loitering/Sprint/Baggage, Night Movement)
        alerts = self.coordinator.process(
            proc_frame,
            t1_dets,
            t3_dets,
            tracked_dets,
            boundary_line=self.boundary_line,
            is_night=is_night,
        )

        # 8. Visualization
        annotated = draw_detections(
            proc_frame,
            tracked_dets,
            boundary_line=self.boundary_line,
            perimeter_polygon=self.perimeter_polygon,
            crossing_ids=self.coordinator.virtual_fence._breached_tracks,
            show_tier=False,
            is_night=is_night,
        )

        return annotated, alerts

    async def run_loop(self):
        self.is_running = True
        logger.info(
            "[%s] Starting camera pipeline worker (Target FPS: %d, Async Inference: %s)",
            self.camera_id,
            settings.pipeline.target_fps,
            self._async_inference,
        )

        try:
            self._source_instance = source_from_config(self.camera_cfg)
        except Exception as e:
            logger.error("[%s] Failed to initialize source: %s", self.camera_id, e)
            return

        source = self._source_instance
        frame_interval = 1.0 / max(5, settings.pipeline.target_fps)

        def frame_reader_loop():
            try:
                src = self._source_instance
                if not src:
                    return
                for frame in src.frames():
                    if self._stop_reader_ev.is_set() or not self.is_running:
                        break
                    # Keep latest frame, drop stale frames when saturated
                    if self._frame_in_queue.full():
                        try:
                            self._frame_in_queue.get_nowait()
                        except queue.Empty:
                            pass
                    try:
                        self._frame_in_queue.put(frame, timeout=0.05)
                    except queue.Full:
                        pass
            except Exception as e:
                logger.error("[%s] Frame ingestion exception: %s", self.camera_id, e)
            finally:
                logger.info("[%s] Ingestion thread terminated", self.camera_id)

        self._stop_reader_ev.clear()
        self._reader_thread = threading.Thread(
            target=frame_reader_loop,
            daemon=True,
            name=f"ingest_{self.camera_id}",
        )
        self._reader_thread.start()

        # Launch decoupled async inference worker task
        if self._async_inference:
            self._inference_task = asyncio.create_task(self._run_inference_loop())

        while self.is_running:
            try:
                # Drain queue to guarantee zero-lag live frame delivery (always process freshest frame)
                frame = None
                while not self._frame_in_queue.empty():
                    try:
                        frame = self._frame_in_queue.get_nowait()
                    except queue.Empty:
                        break
                if frame is None:
                    try:
                        frame = self._frame_in_queue.get_nowait()
                    except queue.Empty:
                        frame = None

                if not self.is_running:
                    break
                if frame is None:
                    if self._reader_thread and not self._reader_thread.is_alive() and self._frame_in_queue.empty():
                        logger.warning("[%s] Ingestion source offline or disconnected. Retrying in 3.0s...", self.camera_id)
                        await asyncio.sleep(3.0)
                        if not self.is_running:
                            break
                        try:
                            self._source_instance = source_from_config(self.camera_cfg)
                            self._stop_reader_ev.clear()
                            self._reader_thread = threading.Thread(
                                target=frame_reader_loop,
                                daemon=True,
                                name=f"ingest_{self.camera_id}",
                            )
                            self._reader_thread.start()
                        except Exception as e:
                            logger.error("[%s] Source reconnect failed: %s", self.camera_id, e)
                        continue
                    await asyncio.sleep(0.005)
                    continue

                t_start = time.perf_counter()
                self.frame_count += 1

                if self._async_inference:
                    with self._state_lock:
                        self._latest_raw_frame = frame
                        has_fresh = self._has_new_dets
                        if has_fresh:
                            raw_dets = self._cached_merged_dets
                            is_night = self._cached_is_night
                            bg_alerts = list(self._pending_bg_alerts)
                            self._pending_bg_alerts.clear()
                            self._has_new_dets = False
                        else:
                            raw_dets = None
                            is_night = self._cached_is_night
                            bg_alerts = []

                    self._frame_event.set()

                    proc_frame = frame
                    if is_night:
                        proc_frame, _, _ = self.night_switcher.process(frame)

                    if has_fresh and raw_dets is not None:
                        # Re-instantiate Detection objects to isolate track state
                        fresh_dets = [
                            Detection(
                                category=d.category,
                                confidence=d.confidence,
                                bbox=d.bbox,
                                source_tier=d.source_tier,
                                sub_category=d.sub_category,
                                camera_id=self.camera_id,
                                location=self.location,
                                suppressed=d.suppressed,
                            )
                            for d in raw_dets
                        ]
                        tracked_dets = self.tracker.update(fresh_dets, proc_frame.shape)

                        # Smooth bounding boxes to eliminate jitter & deliver fluid tracking
                        for d in tracked_dets:
                            self._smooth_detection_box(d)

                        self._cached_tracked_dets = tracked_dets

                        # Clean stale smoothed box records
                        if len(self._smooth_boxes) > 40:
                            active_tids = {d.track_id for d in tracked_dets if d.track_id is not None}
                            self._smooth_boxes = {k: v for k, v in self._smooth_boxes.items() if k in active_tids}

                        # Update Re-ID Global ID assignment
                        current_track_ids = set()
                        for det in tracked_dets:
                            if det.track_id is not None:
                                current_track_ids.add(det.track_id)
                                if det.track_id not in self.track_global_map:
                                    x1, y1, x2, y2 = [int(v) for v in det.bbox]
                                    crop = proc_frame.img[max(0, y1):min(proc_frame.shape[0], y2), max(0, x1):min(proc_frame.shape[1], x2)]
                                    if crop.size > 0:
                                        hist = cv2.calcHist([crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                                        emb = cv2.normalize(hist, hist).flatten()
                                        matched_gid = self.reid_matcher.match(self.camera_id, emb)
                                        if not matched_gid:
                                             matched_gid = self.reid_matcher._next_global_id()
                                        self.track_global_map[det.track_id] = matched_gid
                                        self.reid_matcher.register_exit(self.camera_id, det.track_id, emb, matched_gid)
                                det.global_id = self.track_global_map.get(det.track_id)
                        self.known_active_tracks = current_track_ids

                        # Tactical Coordinator Analysis (FRS, ANPR, Virtual Fence, Loitering, etc.)
                        alerts = self.coordinator.process(
                            proc_frame,
                            [d for d in fresh_dets if d.source_tier == "tier1_yolo"],
                            [d for d in fresh_dets if d.source_tier == "tier3_motion"],
                            tracked_dets,
                            boundary_line=self.boundary_line,
                            is_night=is_night,
                        )
                        if bg_alerts:
                            alerts.extend(bg_alerts)
                    else:
                        # Sub-frame track persistence with forward kinematic extrapolation
                        h_f, w_f = proc_frame.shape[:2]
                        tracked_dets = []
                        for d in self._cached_tracked_dets:
                            pred_b = None
                            if d.track_id is not None and hasattr(self.tracker, "get_predicted_box"):
                                raw_pred = self.tracker.get_predicted_box(d.track_id, scale=0.60)
                                if raw_pred:
                                    pred_b = (
                                        max(0.0, min(float(w_f - 1), raw_pred[0])),
                                        max(0.0, min(float(h_f - 1), raw_pred[1])),
                                        max(0.0, min(float(w_f), raw_pred[2])),
                                        max(0.0, min(float(h_f), raw_pred[3])),
                                    )
                            if pred_b is None:
                                pred_b = self._smooth_boxes.get(d.track_id, d.bbox) if d.track_id is not None else d.bbox

                            tracked_dets.append(
                                Detection(
                                    category=d.category,
                                    confidence=d.confidence,
                                    bbox=pred_b,
                                    source_tier=d.source_tier,
                                    sub_category=d.sub_category,
                                    camera_id=self.camera_id,
                                    location=self.location,
                                    track_id=d.track_id,
                                    global_id=d.global_id,
                                    is_watchlist_match=getattr(d, "is_watchlist_match", False),
                                    face_name=getattr(d, "face_name", None),
                                    suspect_name=getattr(d, "suspect_name", None),
                                    face_detected=getattr(d, "face_detected", False),
                                    face_bbox=getattr(d, "face_bbox", None),
                                    license_plate=getattr(d, "license_plate", None),
                                    plate_confidence=getattr(d, "plate_confidence", None),
                                    is_suspect_plate=getattr(d, "is_suspect_plate", False),
                                    loitering_seconds=getattr(d, "loitering_seconds", 0.0),
                                    is_sprinting=getattr(d, "is_sprinting", False),
                                    unattended_seconds=getattr(d, "unattended_seconds", 0.0),
                                )
                            )
                        alerts = []

                    # Visualizer
                    annotated = draw_detections(
                        proc_frame,
                        tracked_dets,
                        boundary_line=self.boundary_line,
                        perimeter_polygon=self.perimeter_polygon,
                        crossing_ids=self.coordinator.virtual_fence._breached_tracks,
                        show_tier=False,
                        is_night=is_night,
                    )
                else:
                    # Synchronous fallback
                    annotated, alerts = await asyncio.to_thread(self._process_single_frame, frame)

                # Broadcast alerts
                for alert in alerts:
                    await self.broadcast_alert_cb(alert.model_dump(mode="json"))

                # Encode JPEG and push to WebSocket
                try:
                    jpeg_bytes = encode_jpeg(annotated, quality=65)
                    await self.broadcast_frame_cb(self.camera_id, jpeg_bytes)
                except Exception as e:
                    logger.debug("[%s] Broadcast error: %s", self.camera_id, e)

                elapsed = time.perf_counter() - t_start
                inst_fps = 1.0 / max(0.0001, elapsed)
                self._fps_window.append(inst_fps)
                if len(self._fps_window) > 100:
                    self._fps_window.pop(0)
                self.current_fps = round(sum(self._fps_window) / len(self._fps_window), 1)

                if self.frame_count % max(100, settings.pipeline.target_fps) == 0:
                    logger.info(
                        "[%s] High-Throughput Performance: %.1f FPS (render latency: %.2f ms, target: %d FPS)",
                        self.camera_id,
                        self.current_fps,
                        elapsed * 1000,
                        settings.pipeline.target_fps,
                    )

                delay = frame_interval - elapsed
                if delay > 0.001:
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(0.0001)

            except Exception as exc:
                logger.error("[%s] Worker error: %s. Reconnecting in 2s...", self.camera_id, exc)
                await asyncio.sleep(2.0)

    def stop(self):
        self.is_running = False
        self._stop_reader_ev.set()
        source = self._source_instance
        if source is not None and hasattr(source, "stop"):
            try:
                source.stop()
            except Exception:
                pass
        if self._inference_task:
            self._inference_task.cancel()
        if self.task:
            self.task.cancel()


class SurveillanceEngine:
    def __init__(self, broadcast_frame_cb, broadcast_alert_cb):
        self.broadcast_frame_cb = broadcast_frame_cb
        self.broadcast_alert_cb = broadcast_alert_cb

        model_name = getattr(settings.detection, "tier1_model", "yolo12n.pt")
        logger.info("Initializing Tier-1 YOLOv12 Detector (%s)...", model_name)
        self.detector_t1 = Tier1Detector(model_path=model_name)
        self.detector_t2 = Tier2SAHIDetector(model=self.detector_t1._model)
        self.reid_matcher = CrossCameraReIDMatcher()
        self.workers: Dict[str, CameraPipelineWorker] = {}
        self._is_running = False

    def load_cameras_from_registry(self, registry_path: Optional[Path] = None):
        reg_path = registry_path or REGISTRY_PATH
        try:
            if reg_path.exists():
                with open(reg_path, "r") as f:
                    data = json.load(f)
                cameras = data.get("cameras", [])
            else:
                cameras = []
        except Exception as e:
            logger.error("Failed to load camera registry: %s", e)
            cameras = []

        for cam_cfg in cameras:
            if cam_cfg.get("enabled", True):
                cid = cam_cfg["camera_id"]
                if cid not in self.workers:
                    worker = CameraPipelineWorker(
                        cam_cfg,
                        self.detector_t1,
                        self.reid_matcher,
                        self.broadcast_frame_cb,
                        self.broadcast_alert_cb,
                        detector_t2=self.detector_t2,
                    )
                    self.workers[cid] = worker
                    logger.info("Registered worker for camera '%s' (%s)", cid, cam_cfg.get("location"))

    def save_registry(self):
        """Save current camera workers configuration to camera_registry.json."""
        try:
            cam_list = [w.camera_cfg for w in self.workers.values()]
            with open(REGISTRY_PATH, "w") as f:
                json.dump({"cameras": cam_list}, f, indent=2)
            logger.info("Saved %d cameras to %s", len(cam_list), REGISTRY_PATH)
        except Exception as e:
            logger.error("Failed to save camera registry: %s", e)

    def add_camera(self, cam_cfg: dict) -> bool:
        """Add a camera dynamically at runtime."""
        cid = cam_cfg.get("camera_id")
        if not cid:
            return False

        # If camera already running, stop previous instance
        if cid in self.workers:
            self.workers[cid].stop()
            self.workers.pop(cid, None)

        worker = CameraPipelineWorker(
            cam_cfg,
            self.detector_t1,
            self.reid_matcher,
            self.broadcast_frame_cb,
            self.broadcast_alert_cb,
            detector_t2=self.detector_t2,
        )
        self.workers[cid] = worker

        if self._is_running:
            worker.task = asyncio.create_task(worker.run_loop())

        self.save_registry()
        logger.info("[SurveillanceEngine] Added camera: %s", cid)
        return True

    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera dynamically at runtime."""
        if camera_id in self.workers:
            self.workers[camera_id].stop()
            self.workers.pop(camera_id, None)
            self.save_registry()
            logger.info("[SurveillanceEngine] Removed camera: %s", camera_id)
            return True
        return False

    def reload_watchlist(self):
        """Reload watchlist and face embeddings across all active camera workers."""
        count = 0
        for worker in self.workers.values():
            if hasattr(worker, "coordinator"):
                if hasattr(worker.coordinator, "face_detector"):
                    worker.coordinator.face_detector.reload_gallery()
                if hasattr(worker.coordinator, "anpr_detector"):
                    worker.coordinator.anpr_detector._load_watchlist()
                count += 1
        logger.info("[SurveillanceEngine] Watchlist (FRS & ANPR) reloaded across %d active camera workers.", count)

    async def start(self):
        self._is_running = True
        self.load_cameras_from_registry()
        logger.info("Starting %d camera workers...", len(self.workers))
        for cid, worker in self.workers.items():
            worker.task = asyncio.create_task(worker.run_loop())

    async def stop(self):
        self._is_running = False
        logger.info("Stopping all camera workers...")
        for cid, worker in self.workers.items():
            worker.stop()
        self.workers.clear()
