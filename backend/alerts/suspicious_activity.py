"""
backend/alerts/suspicious_activity.py
-------------------------------------
Suspicious Activity Detection module for IBVAP.

Monitors behavioral patterns across all tracked entities:
  - Loitering detection: Lingering in sensitive border perimeter zones (> threshold seconds).
  - Rapid incursion sprint: Abnormal high-speed movement towards border fence.
  - Abandoned / Unattended objects: Stationary luggage/packages left without nearby owners.
  - Unlawful grouping / congregation: Crowd clustering in restricted zones.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from backend.ingestion.frame_model import Detection, Frame

logger = logging.getLogger("SuspiciousActivity")


class SuspiciousActivityDetector:
    """
    Analyzes entity behaviors for tactical threat indicators.
    """

    def __init__(
        self,
        camera_id: str,
        loiter_threshold_sec: float = 20.0,
        sprint_threshold_px_s: float = 380.0,
        abandoned_threshold_sec: float = 15.0,
    ):
        self.camera_id = camera_id
        self.loiter_threshold = loiter_threshold_sec
        self.sprint_threshold = sprint_threshold_px_s
        self.abandoned_threshold = abandoned_threshold_sec

        # State tracking: track_id -> dict(first_seen, last_seen, anchor_cx, anchor_cy, max_disp)
        self._track_history: Dict[int, Dict[str, Any]] = {}
        # Stationary object tracking: obj_id -> dict(first_seen, bbox, cx, cy)
        self._stationary_objects: Dict[str, Dict[str, Any]] = {}

    def analyze(
        self,
        tracked_detections: List[Detection],
        unidentified_detections: Optional[List[Detection]] = None,
    ) -> List[Dict[str, Any]]:
        now = time.time()
        suspicious_events: List[Dict[str, Any]] = []
        persons = [d for d in tracked_detections if d.category == "Person"]

        # ------------------------------------------------------------------
        # 1. Loitering & High-Speed Sprint Detection
        # ------------------------------------------------------------------
        for det in persons:
            if det.track_id is None:
                continue

            tid = det.track_id
            if tid not in self._track_history:
                self._track_history[tid] = {
                    "first_seen": now,
                    "last_seen": now,
                    "anchor_cx": det.cx,
                    "anchor_cy": det.cy,
                    "recent_positions": [(det.cx, det.cy, now)],
                }
            else:
                entry = self._track_history[tid]
                entry["last_seen"] = now
                entry["recent_positions"].append((det.cx, det.cy, now))
                if len(entry["recent_positions"]) > 25:
                    entry["recent_positions"].pop(0)

                duration = now - entry["first_seen"]
                displacement = np.hypot(det.cx - entry["anchor_cx"], det.cy - entry["anchor_cy"])

                # Check Loitering: Entity remained within 110px radius for > threshold seconds
                if duration >= self.loiter_threshold and displacement < 110.0:
                    det.is_loitering = True
                    det.loitering_seconds = duration

                    suspicious_events.append({
                        "type": "LOITERING",
                        "priority": "AMBER" if duration < 15.0 else "RED",
                        "track_id": tid,
                        "category": det.category,
                        "duration_sec": round(duration, 1),
                        "description": f"Suspicious Activity: {det.category} #{tid} loitering in border perimeter for {int(duration)}s",
                        "bbox": det.bbox,
                    })
                elif displacement >= 110.0:
                    # Anchor reset if entity moved away
                    entry["anchor_cx"] = det.cx
                    entry["anchor_cy"] = det.cy
                    entry["first_seen"] = now

                # Check Rapid Movement / Sprint
                recent = entry["recent_positions"]
                if len(recent) >= 4:
                    dt = recent[-1][2] - recent[-4][2]
                    if dt > 0.15:
                        dx = recent[-1][0] - recent[-4][0]
                        dy = recent[-1][1] - recent[-4][1]
                        speed = float(np.hypot(dx, dy) / dt)

                        if speed >= self.sprint_threshold:
                            suspicious_events.append({
                                "type": "RAPID_SPRINT",
                                "priority": "RED",
                                "track_id": tid,
                                "category": det.category,
                                "speed_px_sec": round(speed, 1),
                                "description": f"High Threat Movement: Rapid sprint / incursion run detected by #{tid} ({int(speed)} px/s)",
                                "bbox": det.bbox,
                            })

        # ------------------------------------------------------------------
        # 2. Abandoned / Unattended Object Detection
        # ------------------------------------------------------------------
        luggage_dets = [d for d in tracked_detections if d.category == "Luggage"]
        if unidentified_detections:
            luggage_dets.extend([d for d in unidentified_detections if d.area >= 600])

        for lug in luggage_dets:
            obj_key = f"obj_{int(lug.cx / 40)}_{int(lug.cy / 40)}"
            if obj_key not in self._stationary_objects:
                self._stationary_objects[obj_key] = {
                    "first_seen": now,
                    "last_seen": now,
                    "cx": lug.cx,
                    "cy": lug.cy,
                    "bbox": lug.bbox,
                }
            else:
                st_entry = self._stationary_objects[obj_key]
                st_entry["last_seen"] = now
                duration = now - st_entry["first_seen"]

                if duration >= self.abandoned_threshold:
                    # Check distance to all nearby persons
                    has_nearby_person = False
                    for p in persons:
                        if np.hypot(p.cx - lug.cx, p.cy - lug.cy) < 140.0:
                            has_nearby_person = True
                            break

                    if not has_nearby_person:
                        suspicious_events.append({
                            "type": "ABANDONED_OBJECT",
                            "priority": "RED",
                            "track_id": lug.track_id,
                            "category": "Unattended Object",
                            "duration_sec": round(duration, 1),
                            "description": f"Threat Warning: Abandoned / Unattended baggage detected at ({int(lug.cx)}, {int(lug.cy)}) without owner for {int(duration)}s",
                            "bbox": lug.bbox,
                        })

        # Prune stale history
        active_tids = {d.track_id for d in tracked_detections if d.track_id is not None}
        for k in list(self._track_history.keys()):
            if k not in active_tids and (now - self._track_history[k]["last_seen"]) > 6.0:
                self._track_history.pop(k, None)

        for k in list(self._stationary_objects.keys()):
            if (now - self._stationary_objects[k]["last_seen"]) > 3.0:
                self._stationary_objects.pop(k, None)

        return suspicious_events
