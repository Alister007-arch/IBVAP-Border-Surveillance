"""
backend/ingestion/ip_webcam.py
--------------------------------
Android IP Webcam MJPEG stream ingestor (Phase 7).

Connects to the MJPEG stream served by the "IP Webcam" Android app.
Typical URL format: http://<phone-ip>:8080/video

Usage:
    source = IPWebcamSource(
        camera_id="cam_phone_01",
        location="South Entrance",
        mjpeg_url="http://192.168.1.42:8080/video",
    )
    for frame in source.frames():
        ...

Phase: 7
"""

from __future__ import annotations

import logging
import time
import urllib.request
from datetime import datetime
from typing import Iterator, Optional

import cv2
import numpy as np

from backend.ingestion.frame_model import Frame
from backend.ingestion.video_source import BaseVideoSource
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class IPWebcamSource(BaseVideoSource):
    """
    Ingests an Android IP Webcam MJPEG HTTP stream via OpenCV VideoCapture.

    Parameters
    ----------
    mjpeg_url   : Full URL of the MJPEG stream (e.g. http://192.168.1.5:8080/video).
    """

    def __init__(
        self,
        camera_id: str,
        location: str,
        mjpeg_url: str,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.mjpeg_url = mjpeg_url
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )

    def frames(self) -> Iterator[Frame]:
        frame_interval = 1.0 / self.target_fps

        while True:   # reconnect loop
            logger.info("[IPWebcam][%s] Connecting to %s", self.camera_id, self.mjpeg_url)
            cap = cv2.VideoCapture(self.mjpeg_url)

            if not cap.isOpened():
                logger.error(
                    "[IPWebcam][%s] Cannot connect to %s — retrying in 5s",
                    self.camera_id, self.mjpeg_url,
                )
                time.sleep(5)
                continue

            logger.info("[IPWebcam][%s] Connected.", self.camera_id)
            t_last = time.perf_counter()

            while True:
                ok, img = cap.read()
                if not ok:
                    logger.warning(
                        "[IPWebcam][%s] Read failed — reconnecting", self.camera_id
                    )
                    break

                if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                    img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)

                t_now = time.perf_counter()
                elapsed = t_now - t_last
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                t_last = time.perf_counter()

                yield self._make_frame(img)

            cap.release()
            time.sleep(2)   # brief pause before reconnect
