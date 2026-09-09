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
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
        self.boundary_line = camera_cfg.get("boundary", ((0, 240), (854, 240)))
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
        self.task: Optional[asyncio.Task] = None

    def _process_single_frame(self, frame: Frame) -> Tuple[np.ndarray, List[Alert]]:
        """
        Synchronous processing of a single video frame with IBVAP AI suite.
        """
        # 1. Night/Day auto-switch & preprocessing
        proc_frame, is_night, avg_lum = self.night_switcher.process(frame)

        # 2. Tier-1 Detection (YOLOv8)
        conf_thresh = (
            settings.detection.night_confidence
            if is_night
            else settings.detection.day_confidence
        )
        t1_dets = self.detector_t1.detect(proc_frame, confidence=conf_thresh)

        # 2.1 Tier-2 Sliced Airspace Detection (SAHI for Drones / Small Air Threats)
        t2_dets = self.detector_t2.detect(proc_frame, confidence=conf_thresh) if self.detector_t2 else []

        # 3. Tier-3 Motion Catch-all (Adaptive MOG2 Fallback)
        t3_dets = self.motion_detector.detect(proc_frame)

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
        logger.info("[%s] Starting camera pipeline worker", self.camera_id)

        try:
            source: BaseVideoSource = source_from_config(self.camera_cfg)
        except Exception as e:
            logger.error("[%s] Failed to initialize source: %s", self.camera_id, e)
            return

        frame_interval = 1.0 / max(5, settings.pipeline.target_fps)

        def make_iterator():
            try:
                return iter(source.frames())
            except Exception as ex:
                logger.error("[%s] Error initializing frames iterator: %s", self.camera_id, ex)
                return None

        frame_iter = await asyncio.to_thread(make_iterator)
        if frame_iter is None:
            return

        def fetch_next_frame():
            try:
                return next(frame_iter)
            except StopIteration:
                return None
            except Exception as e:
                logger.debug("[%s] Frame read exception: %s", self.camera_id, e)
                return None

        while self.is_running:
            try:
                frame = await asyncio.to_thread(fetch_next_frame)
                if not self.is_running:
                    break
                if frame is None:
                    await asyncio.sleep(0.5)
                    continue

                t_start = time.perf_counter()
                self.frame_count += 1

                # Run heavy inference in worker threadpool
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
                delay = max(0.01, frame_interval - elapsed)
                await asyncio.sleep(delay)

            except Exception as exc:
                logger.error("[%s] Worker error: %s. Reconnecting in 2s...", self.camera_id, exc)
                await asyncio.sleep(2.0)

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()


class SurveillanceEngine:
    def __init__(self, broadcast_frame_cb, broadcast_alert_cb):
        self.broadcast_frame_cb = broadcast_frame_cb
        self.broadcast_alert_cb = broadcast_alert_cb

        logger.info("Initializing Tier-1 YOLO Detector...")
        self.detector_t1 = Tier1Detector(model_path="yolov8n.pt")
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
