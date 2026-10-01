"""
backend/config/settings.py
--------------------------
Central configuration loader.  Reads thresholds.yaml and exposes typed
settings objects used across all pipeline modules.

Phase 1 only uses the DETECTION thresholds and CAMERA_REGISTRY stub.
All other settings are loaded but gracefully ignored until their phase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Dataclasses (typed config objects)
# ---------------------------------------------------------------------------

@dataclass
class DetectionSettings:
    tier1_model: str = "yolov8n.pt"
    tier1_imgsz: int = 480
    day_confidence: float = 0.25
    night_confidence: float = 0.20
    night_brightness_threshold: int = 60   # 0-255 mean pixel brightness
    tier2_slice_height: int = 320
    tier2_slice_width: int = 320
    tier2_overlap_ratio: float = 0.2
    tier2_airspace_only: bool = True       # Focus sliced inference on upper airspace (top 65% of frame)
    tier2_cadence: int = 10                # Run sliced inference every 10 frames (or on airspace motion)
    tier3_min_contour_area: int = 200      # px² - adaptive small target threshold
    detection_stride: int = 1              # Run full YOLO inference every N frames (1=all frames)


@dataclass
class TrackingSettings:
    max_lost_frames: int = 40
    min_hits: int = 1



@dataclass
class ReIDSettings:
    embedding_cosine_threshold: float = 0.65
    gallery_ttl_seconds: int = 300          # how long embeddings stay in gallery


@dataclass
class AlertSettings:
    group_distance_threshold: float = 100.0    # pixels
    group_velocity_threshold: float = 20.0     # px/frame
    loitering_frames: int = 150
    boundary_crossing_priority: str = "RED"
    group_priority: str = "AMBER"
    unidentified_priority: str = "GRAY"


@dataclass
class PipelineSettings:
    target_fps: int = 180
    async_inference: bool = True
    frame_width: int = 854
    frame_height: int = 480
    preview_enabled: bool = True


@dataclass
class Settings:
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    tracking: TrackingSettings = field(default_factory=TrackingSettings)
    reid: ReIDSettings = field(default_factory=ReIDSettings)
    alerts: AlertSettings = field(default_factory=AlertSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Settings":
        """
        Load settings from a YAML file.  Falls back to all-defaults if the
        file does not exist — safe for Phase 1 fresh starts.
        """
        if path is None:
            path = CONFIG_DIR / "thresholds.yaml"

        obj = cls()

        try:
            with open(path, "r") as fh:
                raw: dict[str, Any] = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            return obj   # use defaults

        def _apply(dataclass_obj, raw_dict: dict) -> None:
            for key, val in raw_dict.items():
                if hasattr(dataclass_obj, key):
                    setattr(dataclass_obj, key, val)

        _apply(obj.detection, raw.get("detection", {}))
        _apply(obj.tracking, raw.get("tracking", {}))
        _apply(obj.reid, raw.get("reid", {}))
        _apply(obj.alerts, raw.get("alerts", {}))
        _apply(obj.pipeline, raw.get("pipeline", {}))

        return obj


# Module-level singleton — import this everywhere
settings = Settings.load()
