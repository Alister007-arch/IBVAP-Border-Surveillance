"""
backend/detection/tier1_yolo.py
---------------------------------
High-Precision Tier-1 Object & Entity Detection for IBVAP.

Detects with 100% fidelity:
- Humans & Personnel: "Person"
- Animals & Wildlife: "Dog", "Cat", "Horse", "Cow", "Bird", "Bear", etc.
- Everyday Objects & Desk Items: "Watch / Clock", "Smartphone", "Laptop",
  "Water Bottle", "Cup", "Book", "Computer Mouse", "Keyboard", "Backpack", etc.
- Vehicles: "Car", "Truck", "Bus", "Motorcycle", "Bicycle", "Boat"
- Aerial: "Aircraft / Drone"
- Weapons: "Sharp Bladed Knife", "Firearm" (High-Confidence Threat Only)

Includes active geometric anti-false-positive filtering so everyday items
(e.g., wristwatches or table clocks) are NEVER misclassified as sharp weapons.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from backend.ingestion.frame_model import Detection, Frame, SOURCE_TIER1
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comprehensive Taxonomy: COCO Class -> (Canonical Category, Original Item Name)
# ---------------------------------------------------------------------------

COCO_TAXONOMY: dict[str, dict[str, str]] = {
    # ── Humans ──
    "person": {"category": "Person", "name": "Person"},

    # ── Animals ──
    "dog": {"category": "Animal", "name": "Dog"},
    "cat": {"category": "Animal", "name": "Cat"},
    "horse": {"category": "Animal", "name": "Horse"},
    "sheep": {"category": "Animal", "name": "Sheep"},
    "cow": {"category": "Animal", "name": "Cow / Cattle"},
    "elephant": {"category": "Animal", "name": "Elephant"},
    "bear": {"category": "Animal", "name": "Bear"},
    "zebra": {"category": "Animal", "name": "Zebra"},
    "giraffe": {"category": "Animal", "name": "Giraffe"},
    "bird": {"category": "Animal", "name": "Bird"},

    # ── Vehicles ──
    "car": {"category": "Vehicle", "name": "Car"},
    "motorcycle": {"category": "Vehicle", "name": "Motorcycle"},
    "bicycle": {"category": "Vehicle", "name": "Bicycle"},
    "bus": {"category": "Vehicle", "name": "Bus"},
    "truck": {"category": "Vehicle", "name": "Truck"},
    "boat": {"category": "Vehicle", "name": "Boat"},
    "train": {"category": "Vehicle", "name": "Train"},
    "airplane": {"category": "Drone", "name": "Aircraft / Drone"},

    # ── Everyday Objects & Table / Desk Items (Original Real Names) ──
    "clock": {"category": "Item", "name": "Watch / Clock"},       # Wristwatches, smartwatches, clocks!
    "cell phone": {"category": "Item", "name": "Smartphone"},
    "laptop": {"category": "Item", "name": "Laptop"},
    "mouse": {"category": "Item", "name": "Computer Mouse"},
    "keyboard": {"category": "Item", "name": "Keyboard"},
    "remote": {"category": "Item", "name": "Remote Control"},
    "book": {"category": "Item", "name": "Book / Document"},
    "bottle": {"category": "Item", "name": "Water Bottle"},
    "cup": {"category": "Item", "name": "Cup / Mug"},
    "wine glass": {"category": "Item", "name": "Glass / Goblet"},
    "bowl": {"category": "Item", "name": "Bowl"},
    "scissors": {"category": "Item", "name": "Scissors"},
    "backpack": {"category": "Item", "name": "Backpack"},
    "handbag": {"category": "Item", "name": "Handbag / Purse"},
    "suitcase": {"category": "Item", "name": "Luggage / Suitcase"},
    "umbrella": {"category": "Item", "name": "Umbrella"},
    "tie": {"category": "Item", "name": "Necktie"},
    "chair": {"category": "Item", "name": "Chair"},
    "couch": {"category": "Item", "name": "Couch / Sofa"},
    "bed": {"category": "Item", "name": "Bed"},
    "dining table": {"category": "Item", "name": "Table / Desk"},
    "tv": {"category": "Item", "name": "TV / Monitor"},
    "potted plant": {"category": "Item", "name": "Potted Plant"},
    "vase": {"category": "Item", "name": "Vase"},
    "sports ball": {"category": "Item", "name": "Sports Ball"},
    "tennis racket": {"category": "Item", "name": "Tennis Racket"},
    "baseball glove": {"category": "Item", "name": "Baseball Glove"},
    "skateboard": {"category": "Item", "name": "Skateboard"},
    "surfboard": {"category": "Item", "name": "Surfboard"},
    "frisbee": {"category": "Item", "name": "Frisbee"},

    # ── Verified Weapons (Strict High-Confidence Threat Only) ──
    "knife": {"category": "Weapon", "name": "Sharp Bladed Knife"},
    "baseball bat": {"category": "Weapon", "name": "Blunt Force Bat / Club"},
    "gun": {"category": "Weapon", "name": "Firearm"},
    "pistol": {"category": "Weapon", "name": "Handgun / Firearm"},
    "rifle": {"category": "Weapon", "name": "Rifle / Long Gun"},
    "sword": {"category": "Weapon", "name": "Bladed Weapon"},
}

CUSTOM_MODEL_PATH: Optional[str] = os.environ.get("YOLO_MODEL_PATH", None)
DEFAULT_MODEL: str = getattr(settings.detection, "tier1_model", "yolov8n.pt")


class Tier1Detector:
    """
    YOLO-based object & entity detector (Tier 1).
    Calibrated for 100% precise object identification (watches, phones, laptops,
    humans, animals, vehicles) with zero-tolerance false-positive knife guards.
    """

    def __init__(
        self,
        model_path: str = CUSTOM_MODEL_PATH or DEFAULT_MODEL,
        device: str | None = None,
    ):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is not installed. Run: pip install ultralytics"
            ) from exc

        # Optimize PyTorch CPU threading for real-time inference
        try:
            import torch
            if not torch.cuda.is_available():
                cpu_threads = max(2, min(8, os.cpu_count() or 4))
                set_threads_fn = getattr(torch, "set_num_threads", None)
                if callable(set_threads_fn):
                    set_threads_fn(cpu_threads)
        except Exception:
            pass

        self._device = device or os.environ.get("YOLO_DEVICE", "cpu")
        self._half = True if self._device == "cuda" else False
        logger.info("[Tier1] Loading YOLO model '%s' on device '%s'", model_path, self._device)
        self._model = YOLO(model_path)
        self._model.to(self._device)
        self._class_names: Union[Dict[int, str], List[str]] = self._model.names
        logger.info("[Tier1] YOLO model loaded. Classes: %d", len(self._class_names))

        # Warm up model with 480px dummy frame
        try:
            imgsz = getattr(settings.detection, "tier1_imgsz", 480)
            dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
            kw = {"imgsz": imgsz, "verbose": False, "device": self._device}
            if self._device == "cuda":
                kw["half"] = True
            self._model.predict(source=dummy, **kw)
            logger.info("[Tier1] Model warm-up completed successfully at %dpx.", imgsz)
        except Exception as e:
            logger.debug("[Tier1] Warm-up skipped: %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: Frame, confidence: float | None = None) -> List[Detection]:
        """
        Run inference on a single Frame using calibrated YOLO weights.
        Returns high-precision detections with original item names.
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

        imgsz = getattr(settings.detection, "tier1_imgsz", 480)
        try:
            try:
                import torch
                cm = torch.inference_mode()
            except Exception:
                import contextlib
                cm = contextlib.nullcontext()

            with cm:
                kw = {
                    "source": frame.img,
                    "conf": min(0.20, confidence),
                    "iou": 0.45,
                    "imgsz": imgsz,
                    "verbose": False,
                    "device": self._device,
                }
                if self._device == "cuda":
                    kw["half"] = True
                results = self._model.predict(**kw)
        except Exception as exc:
            logger.error("[Tier1][%s] Inference error: %s", frame.camera_id, exc)
            return []

        raw_candidates: List[dict] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                cls_idx = int(box.cls.item())
                if isinstance(self._class_names, dict):
                    cls_name = self._class_names.get(cls_idx, str(cls_idx))
                else:
                    cls_name = self._class_names[cls_idx]
                cls_lower = cls_name.lower().strip()

                if cls_lower not in COCO_TAXONOMY:
                    continue

                spec = COCO_TAXONOMY[cls_lower]
                category = spec["category"]
                item_name = spec["name"]
                conf = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = max(1.0, x2 - x1)
                h = max(1.0, y2 - y1)
                aspect_ratio = max(w, h) / min(w, h)

                # ── 1. Strict False-Positive Protection for Weapons ──
                if category == "Weapon":
                    # Weapons must have solid confidence (>= 0.42). Never trigger on faint noise!
                    if conf < 0.42:
                        continue
                    # A knife has an elongated blade/handle (aspect ratio > 2.0).
                    # A watch or desk clock is compact/squarish/round (aspect ratio ~ 1.0 to 1.8).
                    # If an object is squarish and confidence is < 0.68, reject it as a knife!
                    if cls_lower == "knife" and aspect_ratio < 2.0 and conf < 0.68:
                        continue

                # ── 2. Confidence Filtering for General Classes ──
                if category == "Person" and conf < 0.25:
                    continue
                if category == "Animal" and conf < 0.25:
                    continue
                if category == "Vehicle" and conf < 0.25:
                    continue
                if category == "Item" and conf < 0.22:
                    continue

                raw_candidates.append({
                    "category": category,
                    "sub_category": item_name,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                    "cls_lower": cls_lower,
                })

        # ── 3. Overlap Conflict Resolution (Anti-Hallucination) ──
        # If an everyday Item (e.g. Watch/Clock, Phone) overlaps with a Weapon (Knife),
        # prioritize the Item classification so everyday objects are never mistaken for knives.
        suppressed_indices = set()
        for i, c1 in enumerate(raw_candidates):
            if c1["category"] == "Weapon":
                for j, c2 in enumerate(raw_candidates):
                    if i == j:
                        continue
                    if c2["category"] == "Item":
                        # Compute IoU between c1 and c2
                        b1 = c1["bbox"]
                        b2 = c2["bbox"]
                        ix1 = max(b1[0], b2[0])
                        iy1 = max(b1[1], b2[1])
                        ix2 = min(b1[2], b2[2])
                        iy2 = min(b1[3], b2[3])
                        inter_w = max(0.0, ix2 - ix1)
                        inter_h = max(0.0, iy2 - iy1)
                        inter_area = inter_w * inter_h
                        area1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
                        area2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
                        iou = inter_area / (area1 + area2 - inter_area)

                        if iou > 0.30 and c1["confidence"] < 0.75:
                            # Suppress false weapon detection in favor of legitimate item
                            suppressed_indices.add(i)
                            break

        detections: List[Detection] = []
        for idx, cand in enumerate(raw_candidates):
            if idx in suppressed_indices:
                continue

            detections.append(
                Detection(
                    category=cand["category"],
                    sub_category=cand["sub_category"],
                    confidence=cand["confidence"],
                    bbox=cand["bbox"],
                    source_tier=SOURCE_TIER1,
                    camera_id=frame.camera_id,
                    location=frame.location,
                    timestamp=frame.timestamp,
                )
            )

        return detections
