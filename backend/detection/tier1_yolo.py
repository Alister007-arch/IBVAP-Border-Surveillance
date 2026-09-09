"""
backend/detection/tier1_yolo.py
---------------------------------
Tier-1 Detection: YOLOv8 pretrained on COCO.

Detects: person, bicycle, car, motorcycle, bus, truck, boat (vehicles),
         bird, cat, dog, horse, sheep, cow (animals), and all other COCO classes.

Design notes
------------
- The model is loaded once at module level and reused across all calls.
- `detect(frame)` returns a list of Detection objects.
- Confidence threshold is pulled from settings and can differ day vs night.
- An extension point (`CUSTOM_MODEL_PATH`) is exposed so a fine-tuned
  checkpoint can replace the pretrained weights without touching this file.
- COCO class names are mapped to the four canonical categories the alert
  system uses: "Person", "Vehicle", "Animal", or the raw COCO name.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from backend.ingestion.frame_model import Detection, Frame, SOURCE_TIER1
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category mapping: COCO class name → canonical alert category
# ---------------------------------------------------------------------------

COCO_TO_CATEGORY: dict[str, str] = {
    # People (Primary Security Target)
    "person": "Person",
    # Weapons & Sharp Threat Objects
    "knife": "Weapon",
    "scissors": "Weapon",
    "baseball bat": "Weapon",
    "gun": "Weapon",
    "pistol": "Weapon",
    "rifle": "Weapon",
    "sword": "Weapon",
    # Perimeter Vehicles
    "car": "Vehicle",
    "motorcycle": "Vehicle",
    "truck": "Vehicle",
    "bus": "Vehicle",
    # Contraband / Unattended Luggage
    "backpack": "Luggage",
    "handbag": "Luggage",
    "suitcase": "Luggage",
}

WEAPON_SUBCATEGORIES: dict[str, str] = {
    "knife": "Knife / Bladed Weapon",
    "scissors": "Sharp Bladed Instrument",
    "baseball bat": "Blunt Force Weapon",
    "gun": "Firearm",
    "pistol": "Handgun / Firearm",
    "rifle": "Rifle / Long Gun",
    "sword": "Bladed Weapon",
}

# ---------------------------------------------------------------------------
# Extension point: set CUSTOM_MODEL_PATH env var (or edit here) to replace
# the default pretrained weights with a fine-tuned checkpoint.
# ---------------------------------------------------------------------------
CUSTOM_MODEL_PATH: Optional[str] = os.environ.get("YOLO_MODEL_PATH", None)
DEFAULT_MODEL: str = "yolov8n.pt"   # nano — fastest; swap to yolov8s/m for accuracy


class Tier1Detector:
    """
    YOLOv8-based object detector (Tier 1).

    Instantiate once and call `detect(frame)` for each frame.

    Parameters
    ----------
    model_path      : Path to a YOLO .pt checkpoint.  Defaults to yolov8n.pt
                      (downloaded automatically by ultralytics on first run).
    device          : "cpu", "cuda", or "mps".  Defaults to "cpu" for
                      portability; override via YOLO_DEVICE env var.
    """

    def __init__(
        self,
        model_path: str = CUSTOM_MODEL_PATH or DEFAULT_MODEL,
        device: str | None = None,
    ):
        try:
            from ultralytics import YOLO  # lazy import so module loads even without ultralytics
        except ImportError as exc:
            raise ImportError(
                "ultralytics is not installed.  Run: pip install ultralytics"
            ) from exc

        self._device = device or os.environ.get("YOLO_DEVICE", "cpu")
        logger.info("[Tier1] Loading YOLO model '%s' on device '%s'", model_path, self._device)
        self._model = YOLO(model_path)
        self._model.to(self._device)
        self._class_names: list[str] = self._model.names   # index → name
        logger.info("[Tier1] Model loaded.  Classes: %d", len(self._class_names))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: Frame, confidence: float | None = None) -> List[Detection]:
        """
        Run inference on a single Frame.
        Filters strictly for security threats: Person, Weapon (Knife/Blunt), Vehicle, Luggage.
        Ignores birds, animals, indoor furniture, and background noise.

        Parameters
        ----------
        frame       : Tagged Frame from the ingestion layer.
        confidence  : Override confidence threshold.  If None, uses settings
                      (day or night threshold based on frame brightness).

        Returns
        -------
        List of Detection objects (may be empty if nothing found).
        """
        if confidence is None:
            is_night = (
                frame.compute_brightness() < settings.detection.night_brightness_threshold
            )
            confidence = (
                settings.detection.night_confidence
                if is_night
                else settings.detection.day_confidence
            )

        try:
            results = self._model.predict(
                source=frame.img,
                conf=confidence,
                iou=0.45,
                imgsz=416,
                verbose=False,
                device=self._device,
            )
        except Exception as exc:
            logger.error("[Tier1][%s] Inference error: %s", frame.camera_id, exc)
            return []

        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                cls_idx = int(box.cls.item())
                cls_name = self._class_names.get(cls_idx, str(cls_idx)) if isinstance(
                    self._class_names, dict
                ) else self._class_names[cls_idx]
                cls_lower = str(cls_name).lower().strip()

                # STRICT FILTER: Only detect Persons, Weapons (knives/blades), Vehicles, and Luggage
                if cls_lower not in COCO_TO_CATEGORY:
                    continue

                category = COCO_TO_CATEGORY[cls_lower]
                sub_category = None
                if category == "Weapon":
                    sub_category = WEAPON_SUBCATEGORIES.get(cls_lower, "Weapon")
                elif category in ["Vehicle", "Luggage"]:
                    sub_category = cls_lower.capitalize()

                conf = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append(
                    Detection(
                        category=category,
                        sub_category=sub_category,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        source_tier=SOURCE_TIER1,
                        camera_id=frame.camera_id,
                        location=frame.location,
                        timestamp=frame.timestamp,
                    )
                )

        return detections
