"""
backend/ingestion/frame_model.py
---------------------------------
Shared data models for frames and detections.  Every module in the pipeline
works with these objects — keeping them in one place avoids circular imports.

Phase 1: Frame + Detection dataclasses only.
Later phases will extend Detection with embedding fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------

@dataclass
class Frame:
    """
    A single decoded video frame, tagged with metadata before it enters the
    detection pipeline.

    Attributes
    ----------
    camera_id   : Unique camera identifier string (e.g. "cam_01").
    location    : Human-readable location name from the camera registry.
    timestamp   : Wall-clock time when the frame was captured/decoded.
    img         : BGR numpy array (H x W x 3), as returned by OpenCV.
    brightness  : Mean pixel brightness (0–255), computed lazily and cached.
    frame_idx   : Zero-based frame counter for this camera's stream.
    """
    camera_id: str
    location: str
    timestamp: datetime
    img: np.ndarray                    # shape (H, W, 3) BGR uint8
    brightness: float = -1.0           # -1 means "not computed yet"
    frame_idx: int = 0

    def compute_brightness(self) -> float:
        """Compute and cache mean pixel brightness.  Returns cached value on repeat calls."""
        if self.brightness < 0:
            gray = self.img.mean()     # mean of all channels ≈ luminance proxy
            self.brightness = float(gray)
        return self.brightness

    @property
    def shape(self) -> Tuple[int, int, int]:
        return self.img.shape          # (H, W, C)


# ---------------------------------------------------------------------------
# Detection (output of the detection layer)
# ---------------------------------------------------------------------------

SOURCE_TIER1 = "tier1_yolo"
SOURCE_TIER2 = "tier2_sahi"
SOURCE_TIER3 = "tier3_motion"

@dataclass
class Detection:
    """
    A single detection returned by any detection tier.

    Attributes
    ----------
    category    : Class label — e.g. "person", "car", "Drone", "Unidentified".
    confidence  : Detector confidence score [0, 1].
    bbox        : Bounding box as (x1, y1, x2, y2) in pixel coordinates.
    source_tier : Which detection tier produced this (SOURCE_TIER1/2/3).
    track_id    : Assigned by the within-camera tracker (None until tracking stage).
    global_id   : Assigned by cross-camera re-ID (None until reid stage).
    camera_id   : Populated by the ingestion layer via the Frame that triggered this.
    location    : Human-readable camera location (from Frame).
    timestamp   : Timestamp of the originating Frame.
    """
    category: str
    confidence: float
    bbox: Tuple[float, float, float, float]   # (x1, y1, x2, y2)
    source_tier: str

    track_id: Optional[int] = None
    global_id: Optional[str] = None
    camera_id: str = ""
    location: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Phase 5+: embedding vectors (kept None until embedding module activates)
    face_embedding: Optional[np.ndarray] = None
    body_embedding: Optional[np.ndarray] = None

    # IBVAP Analytics metadata
    sub_category: Optional[str] = None         # Specific vehicle type: Car, Truck, Bus, Motorcycle, Bicycle
    face_detected: bool = False
    face_name: Optional[str] = None            # Matched identity from Watchlist (FRS)
    face_bbox: Optional[Tuple[float, float, float, float]] = None
    plate_number: Optional[str] = None         # Detected vehicle plate (ANPR)
    plate_bbox: Optional[Tuple[float, float, float, float]] = None
    is_loitering: bool = False                 # Suspicious activity
    loitering_seconds: float = 0.0

    # Phase 3+: set to True if this detection was merged/suppressed by NMS
    suppressed: bool = False

    @property
    def cx(self) -> float:
        """Centre-x of bounding box."""
        return (self.bbox[0] + self.bbox[2]) / 2.0

    @property
    def cy(self) -> float:
        """Centre-y of bounding box."""
        return (self.bbox[1] + self.bbox[3]) / 2.0

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> dict:
        """JSON-serialisable representation for WebSocket messages."""
        return {
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "bbox": [round(v, 1) for v in self.bbox],
            "source_tier": self.source_tier,
            "track_id": self.track_id,
            "global_id": self.global_id,
            "camera_id": self.camera_id,
            "location": self.location,
            "timestamp": self.timestamp.isoformat(),
        }
