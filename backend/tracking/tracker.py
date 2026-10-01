"""
backend/tracking/tracker.py
-----------------------------
High-Speed Velocity & Spatial Kinematic Tracker for IBVAP.

Key Features:
- Dual-Phase Association:
  1. Primary Phase: High-confidence spatial bounding box overlap (IoU).
  2. High-Speed Phase: Velocity-projected kinematic association for sprinting persons,
     fast-moving border infiltrators, and vehicles crossing the frame at high speeds.
- Continuous Velocity Estimation (vx, vy) with momentum weighting.
- Sub-frame projection support: `get_predicted_box(track_id)` enables 30-60 FPS smooth
  gliding of bounding boxes between YOLO inference passes without jitter or lag.
- Auto-detects fast movement / sprinting (`det.is_sprinting = True`).
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.ingestion.frame_model import Detection
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class TrackedEntity:
    """Internal state for a tracked target."""

    def __init__(self, track_id: int, bbox: Tuple[float, float, float, float], category: str, confidence: float):
        self.track_id = track_id
        self.bbox = bbox
        self.pred_bbox = bbox
        self.velocity: Tuple[float, float] = (0.0, 0.0)
        self.category = category
        self.confidence = confidence
        self.hits = 1
        self.lost = 0

    @property
    def speed(self) -> float:
        vx, vy = self.velocity
        return math.hypot(vx, vy)

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2.0,
            (self.bbox[1] + self.bbox[3]) / 2.0,
        )

    @property
    def predicted_center(self) -> Tuple[float, float]:
        return (
            (self.pred_bbox[0] + self.pred_bbox[2]) / 2.0,
            (self.pred_bbox[1] + self.pred_bbox[3]) / 2.0,
        )


class WithinCameraTracker:
    """
    High-Speed Spatial Kinematic Tracker.
    Maintains persistent local track_id values with velocity-aware predictive association.
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.max_lost_frames = getattr(settings.tracking, "max_lost_frames", 40)
        self._next_id = 1
        self._tracks: Dict[int, TrackedEntity] = {}
        logger.info("[Tracker][%s] High-Speed Velocity Tracker initialized (max_lost=%d)", camera_id, self.max_lost_frames)

    @staticmethod
    def _compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        inter = max(0.0, xB - xA) * max(0.0, yB - yA)
        areaA = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
        areaB = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])
        union = areaA + areaB - inter
        return inter / union if union > 0 else 0.0

    def get_track_velocity(self, track_id: int) -> Tuple[float, float]:
        """Returns the smoothed (vx, vy) velocity vector for a track in pixels/frame."""
        entity = self._tracks.get(track_id)
        return entity.velocity if entity else (0.0, 0.0)

    def get_predicted_box(self, track_id: int, scale: float = 1.0) -> Optional[Tuple[float, float, float, float]]:
        """Returns the linearly extrapolated bounding box for sub-frame rendering."""
        entity = self._tracks.get(track_id)
        if not entity:
            return None
        vx, vy = entity.velocity
        b = entity.bbox
        return (
            b[0] + vx * scale,
            b[1] + vy * scale,
            b[2] + vx * scale,
            b[3] + vy * scale,
        )

    def update(self, detections: List[Detection], frame_shape: tuple) -> List[Detection]:
        """
        Updates tracks with detections.
        Matches targets using IoU first, and predictive kinematic distance for high-speed motion.
        """
        valid_indices = [
            i for i, d in enumerate(detections)
            if not getattr(d, "suppressed", False)
        ]

        # 1. Project all active tracks forward using their velocity
        for entity in self._tracks.values():
            vx, vy = entity.velocity
            b = entity.bbox
            entity.pred_bbox = (b[0] + vx, b[1] + vy, b[2] + vx, b[3] + vy)
            entity.lost += 1

        if not valid_indices:
            # Prune lost tracks
            self._tracks = {
                tid: t for tid, t in self._tracks.items()
                if t.lost <= self.max_lost_frames
            }
            for d in detections:
                d.track_id = None
            return detections

        unmatched_dets = list(valid_indices)
        matched_tracks = set()
        matches: Dict[int, int] = {}  # det_idx -> track_id

        # Phase 1: Spatial IoU matching (matches normal movements & slight shifts)
        for det_idx in list(unmatched_dets):
            det = detections[det_idx]
            det_b = det.bbox
            best_iou = 0.20
            best_tid: Optional[int] = None

            for tid, entity in self._tracks.items():
                if tid in matched_tracks:
                    continue
                # Compare against both current bbox and velocity-predicted bbox
                iou1 = self._compute_iou(det_b, entity.bbox)
                iou2 = self._compute_iou(det_b, entity.pred_bbox)
                iou = max(iou1, iou2)
                if iou > best_iou:
                    best_iou = iou
                    best_tid = tid

            if best_tid is not None:
                matches[det_idx] = best_tid
                matched_tracks.add(best_tid)
                unmatched_dets.remove(det_idx)

        # Phase 2: High-Speed Kinematic Distance Matching (Sprint / Fast Vehicle / Drone)
        # Even if IoU is 0 due to a fast jump, associate by trajectory & velocity
        for det_idx in list(unmatched_dets):
            det = detections[det_idx]
            det_b = det.bbox
            det_cx = (det_b[0] + det_b[2]) / 2.0
            det_cy = (det_b[1] + det_b[3]) / 2.0
            det_w = max(1.0, det_b[2] - det_b[0])
            det_h = max(1.0, det_b[3] - det_b[1])
            diag = math.hypot(det_w, det_h)

            # Adaptive search radius proportional to target size & speed
            max_search_dist = max(160.0, diag * 2.5)

            best_dist = float("inf")
            best_tid: Optional[int] = None

            for tid, entity in self._tracks.items():
                if tid in matched_tracks:
                    continue
                pcx, pcy = entity.predicted_center
                dist = math.hypot(det_cx - pcx, det_cy - pcy)

                # Prioritize same category if possible
                cat_mult = 1.0 if entity.category == det.category else 1.35
                effective_dist = dist * cat_mult

                if effective_dist < max_search_dist and effective_dist < best_dist:
                    best_dist = effective_dist
                    best_tid = tid

            if best_tid is not None:
                matches[det_idx] = best_tid
                matched_tracks.add(best_tid)
                unmatched_dets.remove(det_idx)

        # 3. Update matched tracks & spawn new tracks
        for det_idx in valid_indices:
            det = detections[det_idx]
            b = det.bbox
            new_cx = (b[0] + b[2]) / 2.0
            new_cy = (b[1] + b[3]) / 2.0

            if det_idx in matches:
                tid = matches[det_idx]
                entity = self._tracks[tid]
                old_cx, old_cy = entity.center

                # Update velocity with momentum (70% instantaneous, 30% history)
                inst_vx = new_cx - old_cx
                inst_vy = new_cy - old_cy
                entity.velocity = (
                    0.70 * inst_vx + 0.30 * entity.velocity[0],
                    0.70 * inst_vy + 0.30 * entity.velocity[1],
                )
                entity.bbox = b
                entity.pred_bbox = b
                entity.category = det.category
                entity.confidence = det.confidence
                entity.lost = 0
                entity.hits += 1

                det.track_id = tid
                # Mark sprinting if speed exceeds high-velocity threshold (e.g. > 14 px/frame)
                if entity.speed > 14.0:
                    det.is_sprinting = True
            else:
                # New target enters frame
                tid = self._next_id
                self._next_id += 1
                entity = TrackedEntity(
                    track_id=tid,
                    bbox=b,
                    category=det.category,
                    confidence=det.confidence,
                )
                self._tracks[tid] = entity
                det.track_id = tid

        # 4. Prune dead tracks
        self._tracks = {
            tid: t for tid, t in self._tracks.items()
            if t.lost <= self.max_lost_frames
        }

        return detections
