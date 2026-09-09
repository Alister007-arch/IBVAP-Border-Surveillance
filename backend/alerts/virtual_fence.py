"""
backend/alerts/virtual_fence.py
-------------------------------
Virtual Fence & Intrusion Detection module for IBVAP.

Monitors virtual tripwires and polygonal exclusion corridors along border boundaries.
Triggers immediate high-priority intrusion alerts upon unauthorized perimeter breach.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame

logger = logging.getLogger("VirtualFence")


class VirtualFenceDetector:
    """
    Virtual fence tripwire and perimeter intrusion monitor.
    """

    def __init__(
        self,
        camera_id: str,
        tripwire_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        perimeter_polygon: Optional[List[Tuple[int, int]]] = None,
    ):
        self.camera_id = camera_id
        # Default horizontal tripwire at 50% height if None
        self.tripwire_line = tripwire_line
        self.perimeter_polygon = perimeter_polygon

        # Track trajectory history: track_id -> [(cx, cy, timestamp)]
        self._trajectories: Dict[int, List[Tuple[float, float, float]]] = {}
        # Set of track IDs that have breached
        self._breached_tracks: Set[int] = set()
        self.is_armed: bool = True
        self.last_breach_time: float = 0.0

    def set_tripwire(self, pt1: Tuple[int, int], pt2: Tuple[int, int]):
        self.tripwire_line = (pt1, pt2)

    def set_polygon(self, points: List[Tuple[int, int]]):
        self.perimeter_polygon = points

    def _crosses_line(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        line: Tuple[Tuple[int, int], Tuple[int, int]],
    ) -> bool:
        """Determines if the trajectory segment between p1 and p2 intersects the fence line."""
        (lx1, ly1), (lx2, ly2) = line

        # Standard 2D cross product line-line intersection test
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        A = p1
        B = p2
        C = (float(lx1), float(ly1))
        D = (float(lx2), float(ly2))

        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def check_intrusions(
        self,
        frame_shape: Tuple[int, ...],
        tracked_detections: List[Detection],
    ) -> Tuple[List[Dict[str, Any]], Set[int]]:
        """
        Evaluate tracked entities against the virtual fence perimeter and tripwires.
        Returns:
          - List of intrusion incident dicts
          - Set of currently breaching track IDs
        """
        h, w = frame_shape[:2]
        now = time.time()
        active_breaches: List[Dict[str, Any]] = []
        breached_tids: Set[int] = set()

        # Fallback default boundary line if neither is configured
        fence_line = self.tripwire_line or ((0, int(h * 0.52)), (w, int(h * 0.52)))

        for det in tracked_detections:
            if det.track_id is None:
                continue

            # Infiltration checks strictly target human intrusions or armed penetrations
            if det.category not in ["Person", "Weapon"]:
                continue

            tid = det.track_id
            curr_pos = (det.cx, det.cy, now)

            hist = self._trajectories.setdefault(tid, [])
            hist.append(curr_pos)
            # Retain last 20 trajectory positions (approx 1.5s)
            if len(hist) > 20:
                hist.pop(0)

            has_breached = False
            breach_reason = ""

            # 1. Check Polygonal Exclusion Zone Intrusion
            if self.perimeter_polygon and len(self.perimeter_polygon) >= 3:
                poly_np = np.array(self.perimeter_polygon, dtype=np.int32)
                dist = cv2.pointPolygonTest(poly_np, (det.cx, det.cy), False)
                if dist >= 0:
                    has_breached = True
                    breach_reason = f"Restricted Perimeter Zone Breach by {det.category}"

            # 2. Check Virtual Tripwire Line Crossing
            if not has_breached and len(hist) >= 2:
                prev_pos = (hist[-2][0], hist[-2][1])
                curr_pt = (det.cx, det.cy)
                if self._crosses_line(prev_pos, curr_pt, fence_line):
                    has_breached = True
                    breach_reason = f"Virtual Fence Tripwire Crossed by {det.category}"

            if has_breached:
                breached_tids.add(tid)
                self.last_breach_time = now

                # Speed estimation
                speed_px = 0.0
                if len(hist) >= 3:
                    dx = hist[-1][0] - hist[-3][0]
                    dy = hist[-1][1] - hist[-3][1]
                    dt = hist[-1][2] - hist[-3][2]
                    if dt > 0:
                        speed_px = float(np.hypot(dx, dy) / dt)

                active_breaches.append({
                    "track_id": tid,
                    "category": det.category,
                    "sub_category": det.sub_category,
                    "reason": breach_reason,
                    "position": (det.cx, det.cy),
                    "speed_px_sec": round(speed_px, 1),
                    "bbox": det.bbox,
                    "priority": "RED",
                })

        # Prune trajectories of disappeared tracks
        active_set = {d.track_id for d in tracked_detections if d.track_id is not None}
        dead_keys = [k for k in self._trajectories if k not in active_set and (now - self._trajectories[k][-1][2]) > 5.0]
        for k in dead_keys:
            self._trajectories.pop(k, None)

        return active_breaches, breached_tids
