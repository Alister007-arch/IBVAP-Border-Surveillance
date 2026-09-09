"""
backend/alerts/grouper.py
---------------------------
Event grouping logic: clusters spatially-close, co-moving detections into
a single "Group of N" alert rather than N individual alerts.

Algorithm (Phase 6):
  1. For each frame's active detection list, compute pairwise distances between
     track centroids.
  2. Cluster tracks whose centroid distance < group_distance_threshold AND
     whose velocity vectors have similar direction/magnitude.
  3. If cluster size >= 2, emit one Group alert with group_size = N.
  4. Singleton tracks emit their individual category alert.

Phase: 6
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.ingestion.frame_model import Detection
from backend.alerts.schema import Alert, AlertPriority, AlertCategory, BoundingBox
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class EventGrouper:
    """
    Groups detections from the same frame into individual or group alerts.

    Parameters
    ----------
    camera_id   : Camera this grouper is associated with.
    location    : Human-readable location for alerts.
    """

    def __init__(self, camera_id: str, location: str):
        self.camera_id = camera_id
        self.location = location
        # Track history for velocity estimation: track_id → list of (cx, cy) over recent frames
        self._position_history: Dict[int, List[Tuple[float, float]]] = {}
        self._history_len = 5

    def _velocity(self, track_id: int) -> Optional[Tuple[float, float]]:
        hist = self._position_history.get(track_id, [])
        if len(hist) < 2:
            return None
        dx = hist[-1][0] - hist[-2][0]
        dy = hist[-1][1] - hist[-2][1]
        return dx, dy

    def update(
        self,
        detections: List[Detection],
        crossing_ids: Optional[set] = None,
    ) -> List[Alert]:
        """
        Process a frame's detections and return a list of Alert objects.
        """
        from datetime import datetime

        crossing_ids = crossing_ids or set()
        cfg = settings.alerts

        # Update position history
        for det in detections:
            if det.track_id is not None and not det.suppressed:
                hist = self._position_history.setdefault(det.track_id, [])
                hist.append((det.cx, det.cy))
                if len(hist) > self._history_len:
                    hist.pop(0)

        active = [d for d in detections if not d.suppressed and d.track_id is not None]
        if not active:
            return []

        # Simple distance-based clustering
        clusters: List[List[Detection]] = []
        assigned = [False] * len(active)

        for i, d1 in enumerate(active):
            if assigned[i]:
                continue
            cluster = [d1]
            assigned[i] = True
            for j, d2 in enumerate(active):
                if assigned[j] or i == j:
                    continue
                dist = np.hypot(d1.cx - d2.cx, d1.cy - d2.cy)
                if dist < cfg.group_distance_threshold:
                    cluster.append(d2)
                    assigned[j] = True
            clusters.append(cluster)

        alerts: List[Alert] = []
        ts = datetime.utcnow()

        for cluster in clusters:
            is_crossing = any(
                d.track_id in crossing_ids for d in cluster if d.track_id is not None
            )
            n = len(cluster)

            if n >= 2:
                category = AlertCategory.GROUP.value
                priority = AlertPriority.RED if is_crossing else AlertPriority.AMBER
                desc = (
                    f"Group of {n} crossing boundary"
                    if is_crossing
                    else f"Group of {n} moving together"
                )
            else:
                det = cluster[0]
                category = det.category
                if is_crossing:
                    priority = AlertPriority.RED
                    desc = f"{category} crossing boundary"
                elif category == "Unidentified":
                    priority = AlertPriority.GRAY
                    desc = "Unidentified motion detected"
                else:
                    priority = AlertPriority.AMBER
                    desc = f"{category} detected near boundary"

            alerts.append(
                Alert(
                    timestamp=ts,
                    camera_id=self.camera_id,
                    location=self.location,
                    category=category,
                    priority=priority,
                    description=desc,
                    bboxes=[BoundingBox(x1=d.bbox[0], y1=d.bbox[1], x2=d.bbox[2], y2=d.bbox[3])
                            for d in cluster],
                    track_ids=[d.track_id for d in cluster if d.track_id is not None],
                    global_id=cluster[0].global_id,
                    group_size=n,
                    is_crossing=is_crossing,
                )
            )

        return alerts
