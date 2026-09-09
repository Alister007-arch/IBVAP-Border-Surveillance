"""
backend/tracking/tracker.py
-----------------------------
Within-camera object tracker using supervision's ByteTrack wrapper.

Assigns and maintains persistent local track_id values for each detected
entity within one camera's stream.  One Tracker instance per camera.

Phase: 2
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from backend.ingestion.frame_model import Detection
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class WithinCameraTracker:
    """
    Wraps supervision's ByteTrack to track detections within one camera stream.

    Parameters
    ----------
    camera_id   : Used in log messages.
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        try:
            import supervision as sv
            self._tracker = sv.ByteTrack(
                lost_track_buffer=settings.tracking.max_lost_frames,
                minimum_matching_threshold=0.45,
                minimum_consecutive_frames=1,
            )
        except ImportError as exc:
            raise ImportError(
                "supervision is not installed. Run: pip install supervision"
            ) from exc
        logger.info("[Tracker][%s] ByteTrack tracker initialised with IoU matching.", camera_id)

    @staticmethod
    def _compute_iou(boxA, boxB) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        inter = max(0.0, xB - xA) * max(0.0, yB - yA)
        areaA = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
        areaB = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])
        union = areaA + areaB - inter
        return inter / union if union > 0 else 0.0

    def update(self, detections: List[Detection], frame_shape: tuple) -> List[Detection]:
        """
        Update tracker with the current frame's detections.
        Matches track IDs accurately by spatial bounding-box overlap (IoU)
        to prevent track ID swapping and identity confusion when multiple people are present.
        """
        import supervision as sv

        # Filter out any shadowed/suppressed detections from merger
        valid_dets = [d for d in detections if not getattr(d, "suppressed", False)]

        if not valid_dets:
            empty = sv.Detections.empty()
            self._tracker.update_with_detections(empty)
            for d in detections:
                d.track_id = None
            return detections

        # Build supervision Detections object
        boxes = np.array([list(d.bbox) for d in valid_dets], dtype=np.float32)
        confs = np.array([d.confidence for d in valid_dets], dtype=np.float32)
        class_ids = np.zeros(len(valid_dets), dtype=int)

        sv_dets = sv.Detections(
            xyxy=boxes,
            confidence=confs,
            class_id=class_ids,
        )

        tracked = self._tracker.update_with_detections(sv_dets)

        # Robust spatial IoU association:
        # Match each input detection to the closest tracked box
        if tracked.tracker_id is not None and len(tracked.xyxy) > 0:
            tracked_boxes = tracked.xyxy
            tracked_ids = tracked.tracker_id
            matched_track_indices = set()

            for det in valid_dets:
                best_iou = 0.0
                best_t_idx = -1
                for j in range(len(tracked_boxes)):
                    if j in matched_track_indices:
                        continue
                    iou = self._compute_iou(det.bbox, tracked_boxes[j])
                    if iou > best_iou:
                        best_iou = iou
                        best_t_idx = j

                if best_t_idx >= 0 and best_iou >= 0.25:
                    det.track_id = int(tracked_ids[best_t_idx])
                    matched_track_indices.add(best_t_idx)
                else:
                    det.track_id = None
        else:
            for d in valid_dets:
                d.track_id = None

        return detections
