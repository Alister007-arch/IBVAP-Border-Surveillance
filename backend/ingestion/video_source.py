"""
backend/ingestion/video_source.py
-----------------------------------
Camera source adapters. Each adapter is a generator that yields Frame objects.
All adapters share the same interface:
    frames() -> Iterator[Frame]
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import cv2
import numpy as np

from backend.ingestion.frame_model import Frame
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class BaseVideoSource(ABC):
    def __init__(self, camera_id: str, location: str, target_fps: int = 15):
        self.camera_id = camera_id
        self.location = location
        self.target_fps = target_fps
        self._frame_idx: int = 0
        self._stopped: bool = False

    def stop(self):
        self._stopped = True

    @abstractmethod
    def frames(self) -> Iterator[Frame]:
        ...

    def _make_frame(self, img: np.ndarray) -> Frame:
        frame = Frame(
            camera_id=self.camera_id,
            location=self.location,
            timestamp=datetime.utcnow(),
            img=img,
            frame_idx=self._frame_idx,
        )
        self._frame_idx += 1
        return frame

    def __iter__(self) -> Iterator[Frame]:
        return self.frames()


class VideoFileSource(BaseVideoSource):
    def __init__(
        self,
        camera_id: str,
        location: str,
        source_path: str | Path,
        loop: bool = True,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.source_path = Path(source_path)
        self.loop = loop
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )
        if not self.source_path.is_absolute() and not self.source_path.exists():
            _proj_root = Path(__file__).resolve().parent.parent.parent
            if (_proj_root / self.source_path).exists():
                self.source_path = _proj_root / self.source_path

        if not self.source_path.exists():
            raise FileNotFoundError(
                f"[VideoFileSource] Video file not found: {self.source_path}\n"
                f"Tip: place a sample clip at demo_assets/sample.mp4 or pass "
                f"--source 0 to use your webcam."
            )

    def frames(self) -> Iterator[Frame]:
        # Fast memory buffer for looping video clips (eliminates disk reopen stalls for 150+ FPS)
        if self.loop:
            cap = cv2.VideoCapture(str(self.source_path))
            if cap.isOpened():
                cached_imgs = []
                native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                skip_ratio = max(1, round(native_fps / self.target_fps))
                raw_idx = 0
                while True:
                    ok, img = cap.read()
                    if not ok:
                        break
                    raw_idx += 1
                    if raw_idx % skip_ratio != 0:
                        continue
                    if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                        img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)
                    cached_imgs.append(img)
                    if len(cached_imgs) > 500:  # If clip is very long, stream from disk instead
                        cached_imgs = None
                        break
                cap.release()

                if cached_imgs:
                    logger.info(
                        "[%s] Memory-cached %d frames from '%s' for ultra-high throughput playback (up to 150 FPS)",
                        self.camera_id, len(cached_imgs), self.source_path.name,
                    )
                    while not self._stopped:
                        for img in cached_imgs:
                            if self._stopped:
                                break
                            yield self._make_frame(img)
                    return

        run = True
        while run and not self._stopped:
            cap = cv2.VideoCapture(str(self.source_path))
            if not cap.isOpened():
                logger.error("[%s] Cannot open video file: %s", self.camera_id, self.source_path)
                return

            native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            skip_ratio = max(1, round(native_fps / self.target_fps))
            raw_frame_idx = 0

            logger.info(
                "[%s] Opened '%s' — native %.1f fps (target %d fps)",
                self.camera_id, self.source_path.name, native_fps, self.target_fps,
            )

            while not self._stopped:
                ok, img = cap.read()
                if not ok:
                    break

                raw_frame_idx += 1
                if raw_frame_idx % skip_ratio != 0:
                    continue

                if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                    img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)

                yield self._make_frame(img)

            cap.release()
            if not self.loop or self._stopped:
                run = False


class WebcamSource(BaseVideoSource):
    """
    Stabilized USB Webcam Source with:
    - Windows DirectShow (CAP_DSHOW) backend to eliminate MSMF auto-exposure pulsing & clock jitter
    - Hardware MJPEG fourcc codec to avoid USB bus saturation
    - CAP_PROP_BUFFERSIZE = 1 to prevent stale queued frames
    - Threaded background grabber to continuously drain hardware frames with zero queue backlog
    - Anti-flicker frame retention: holds last valid frame if hardware drops a packet
    """
    def __init__(
        self,
        camera_id: str,
        location: str,
        device_index: int = 0,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.device_index = device_index
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )
        self._running = False
        self._latest_img: Optional[np.ndarray] = None
        self._lock = threading.Lock()

    def _open_capture(self) -> cv2.VideoCapture:
        if sys.platform.startswith("win"):
            try:
                cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
                if cap.isOpened():
                    return cap
                cap.release()
            except Exception:
                pass
        return cv2.VideoCapture(self.device_index)

    def frames(self) -> Iterator[Frame]:
        cap = self._open_capture()
        if not cap.isOpened():
            logger.error("[%s] Cannot open webcam at index %d", self.camera_id, self.device_index)
            return

        # 1. Hardware MJPEG compression to prevent USB bus frame drops
        try:
            fourcc_func = getattr(cv2, "VideoWriter_fourcc", cv2.VideoWriter.fourcc)
            cap.set(cv2.CAP_PROP_FOURCC, fourcc_func(*'MJPG'))
        except Exception:
            pass

        # 2. Buffer size = 1 to eliminate queue backlog stutter
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # 3. Framerate and resolution
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resize_to[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resize_to[1])

        logger.info("[%s] Opened stabilized USB webcam index %d (Anti-Flicker / MJPEG active)", self.camera_id, self.device_index)

        self._running = True
        self._latest_img = None
        self._has_new_frame_ev = threading.Event()
        has_new_frame = self._has_new_frame_ev

        # Dedicated grabber thread continuously reading latest hardware frame
        def grabber_thread():
            while self._running:
                ok, img = cap.read()
                if ok and img is not None and img.size > 0:
                    with self._lock:
                        self._latest_img = img.copy()
                    has_new_frame.set()
                else:
                    time.sleep(0.005)

        t = threading.Thread(target=grabber_thread, daemon=True, name=f"webcam_grab_{self.camera_id}")
        t.start()

        last_yielded_img = None

        try:
            while self._running:
                # Wait up to 1.0s for next hardware frame (instant wake on frame ready)
                has_new_frame.wait(timeout=1.0)
                has_new_frame.clear()

                if not self._running:
                    break

                with self._lock:
                    curr_img = self._latest_img

                # Anti-flicker: if momentarily None, hold previous good frame
                if curr_img is None:
                    curr_img = last_yielded_img

                if curr_img is None:
                    time.sleep(0.01)
                    continue

                last_yielded_img = curr_img

                img_out = curr_img
                if img_out.shape[1] != self.resize_to[0] or img_out.shape[0] != self.resize_to[1]:
                    img_out = cv2.resize(img_out, self.resize_to, interpolation=cv2.INTER_LINEAR)

                yield self._make_frame(img_out)
        finally:
            self._running = False
            has_new_frame.set()
            t.join(timeout=0.5)
            cap.release()
            logger.info("[%s] Stabilized webcam released", self.camera_id)

    def stop(self):
        self._running = False
        if hasattr(self, "_has_new_frame_ev"):
            self._has_new_frame_ev.set()


class IPCCTVSource(BaseVideoSource):
    """
    Standard IP-based CCTV camera adapter supporting RTSP, HTTP, MJPEG streams.
    """

    def __init__(
        self,
        camera_id: str,
        location: str,
        stream_url: str,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.stream_url = str(stream_url)
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )
        self._stopped = False

    def stop(self):
        self._stopped = True

    def frames(self) -> Iterator[Frame]:
        if "phone_stream.html" in self.stream_url.lower() or self.stream_url.lower().endswith(".html"):
            logger.warning(
                "[%s] Stream URL points to a webpage (%s), not a raw video stream. "
                "Mobile phone streaming is handled via the browser streamer client.",
                self.camera_id, self.stream_url
            )
            return

        while not self._stopped:
            cap = cv2.VideoCapture(self.stream_url)
            if not cap.isOpened():
                logger.warning("[%s] Cannot open IP camera feed: %s. Retrying in 4s...", self.camera_id, self.stream_url)
                for _ in range(40):
                    if self._stopped:
                        return
                    time.sleep(0.1)
                continue

            logger.info("[%s] Connected to IP camera stream: %s", self.camera_id, self.stream_url)
            try:
                while not self._stopped:
                    ok, img = cap.read()
                    if not ok or img is None:
                        logger.warning("[%s] IP camera frame drop / reconnecting...", self.camera_id)
                        break

                    if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                        img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)

                    yield self._make_frame(img)
            finally:
                cap.release()

            for _ in range(15):
                if self._stopped:
                    return
                time.sleep(0.1)


def source_from_config(camera_cfg: dict) -> BaseVideoSource:
    cid = camera_cfg["camera_id"]
    loc = camera_cfg.get("location", cid)
    src = camera_cfg["source"]
    kind = camera_cfg.get("type", "file")

    if kind in ["ip_camera", "rtsp", "http", "stream"]:
        return IPCCTVSource(
            camera_id=cid,
            location=loc,
            stream_url=src,
        )
    elif kind == "file":
        return VideoFileSource(
            camera_id=cid,
            location=loc,
            source_path=src,
            loop=camera_cfg.get("loop", True),
        )
    elif kind == "webcam":
        return WebcamSource(
            camera_id=cid,
            location=loc,
            device_index=int(src),
        )
    else:
        raise ValueError(
            f"[source_from_config] Unknown source type '{kind}' for camera '{cid}'."
        )
