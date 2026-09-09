"""
backend/detection/night_switch.py
-----------------------------------
Night / day auto-switching module.

Monitors per-camera frame brightness and:
  - Returns preprocessed (CLAHE-enhanced) frames when brightness < threshold
  - Returns original frames in daytime mode
  - Adjusts confidence threshold recommendation accordingly

Phase: 4
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Frame
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class NightSwitcher:
    """
    Per-camera brightness monitor and CLAHE preprocessor.

    Uses a rolling average of recent frame brightness to avoid flickering
    between day/night modes on transitional lighting.

    Parameters
    ----------
    camera_id       : For logging purposes.
    window_size     : Number of frames to average for the brightness estimate.
    """

    def __init__(self, camera_id: str, window_size: int = 45):
        self.camera_id = camera_id
        self._history: deque[float] = deque(maxlen=window_size)
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._is_night: bool = False

    def process(self, frame: Frame) -> Tuple[Frame, bool, float]:
        """
        Process a frame through the night-mode switcher with hysteresis.
        Prevents flickering/toggling between day and night modes.
        """
        brightness = frame.compute_brightness()
        self._history.append(brightness)
        avg_brightness = float(np.mean(self._history))

        base_threshold = float(settings.detection.night_brightness_threshold)
        hysteresis = 8.0
        was_night = self._is_night

        # Hysteresis band prevents rapid flapping around the boundary
        if was_night:
            if avg_brightness > (base_threshold + hysteresis):
                self._is_night = False
        else:
            if avg_brightness < (base_threshold - hysteresis):
                self._is_night = True

        if self._is_night != was_night:
            mode = "NIGHT" if self._is_night else "DAY"
            logger.info(
                "[NightSwitcher][%s] Switched to %s mode (avg brightness: %.1f, threshold: %.1f ± %.1f)",
                self.camera_id, mode, avg_brightness, base_threshold, hysteresis,
            )

        if self._is_night:
            # Apply CLAHE to the luminance channel (convert BGR → LAB → enhance L → back)
            lab = cv2.cvtColor(frame.img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            l_enhanced = self._clahe.apply(l_channel)
            enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
            enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

            import copy
            enhanced_frame = copy.copy(frame)
            enhanced_frame.img = enhanced_bgr
            enhanced_frame.brightness = float(enhanced_bgr.mean())
            return enhanced_frame, True, avg_brightness

        return frame, False, avg_brightness
