"""
backend/alerts/section_coordinator.py
--------------------------------------
Central Tactical Intelligence Coordinator for IBVAP.

Coordinates all software-driven video analytics modules:
  - Human Detection & Tracking
  - Vehicle Detection & Explicit Classification
  - Facial Recognition System (FRS) & Watchlist Matching
  - Automatic Number Plate Recognition (ANPR) & BOLO Matching
  - Virtual Fence Intrusion & Tripwire Breach Detection
  - Suspicious Activity Detection (Loitering, Rapid Sprint, Abandoned Luggage)
  - Night-Time Movement Detection
  - Drone & Aerial Incursions
  - Persistent SQLite Event Store Logging
"""

from __future__ import annotations

import base64
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from backend.alerts.schema import Alert, AlertPriority, AlertCategory, SectionType, SECTION_TITLES, BoundingBox
from backend.alerts.suspicious_activity import SuspiciousActivityDetector
from backend.alerts.virtual_fence import VirtualFenceDetector
from backend.db.event_store import event_store
from backend.detection.anpr import ANPRDetector
from backend.detection.face_detector import FaceDetector
from backend.ingestion.frame_model import Detection, Frame
from backend.reid.matcher import CrossCameraReIDMatcher

logger = logging.getLogger("SectionCoordinator")


class SectionCoordinator:
    """
    Coordinates and routes all AI detections into tactical intelligence alerts.
    """

    def __init__(
        self,
        camera_id: str,
        location: str,
        reid_matcher: Optional[CrossCameraReIDMatcher] = None,
        boundary_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        perimeter_polygon: Optional[List[Tuple[int, int]]] = None,
    ):
        self.camera_id = camera_id
        self.location = location
        self.reid_matcher = reid_matcher or CrossCameraReIDMatcher()

        # Analytics Submodules
        self.face_detector = FaceDetector()
        self.anpr_detector = ANPRDetector()
        self.virtual_fence = VirtualFenceDetector(
            camera_id=camera_id,
            tripwire_line=boundary_line,
            perimeter_polygon=perimeter_polygon,
        )
        self.suspicious_detector = SuspiciousActivityDetector(camera_id=camera_id)

        # Gallery and cooldowns
        self._appearance_gallery: Dict[int, dict] = {}
        self._recent_incursion_points: List[Tuple[float, float, float]] = []
        self._alert_cooldowns: Dict[str, float] = {}
        self._track_trajectories: Dict[int, List[Tuple[float, float, float]]] = {}

    def _should_emit(self, key: str, cooldown_seconds: float = 3.5) -> bool:
        now = time.time()
        last_time = self._alert_cooldowns.get(key, 0.0)
        if (now - last_time) >= cooldown_seconds:
            self._alert_cooldowns[key] = now
            return True
        return False

    def _extract_crop_b64(self, img: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[str]:
        try:
            h, w = img.shape[:2]
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if (x2 - x1) < 10 or (y2 - y1) < 10:
                return None
            crop = img[y1:y2, x1:x2]
            ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if ok:
                return base64.b64encode(buf).decode("utf-8")
        except Exception:
            pass
        return None

    def _compute_predictive_vector(
        self,
        track_id: Optional[int],
        bbox: Optional[Tuple[float, float, float, float]],
        frame_shape: Tuple[int, int],
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """Calculates trajectory speed, azimuth heading, and predicted perimeter breach ETA."""
        if not bbox:
            return None, None, None
        h, w = frame_shape[:2]
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        now = time.time()
        tid = track_id if track_id is not None else 0
        history = self._track_trajectories.setdefault(tid, [])
        history.append((cx, cy, now))
        if len(history) > 10:
            history.pop(0)

        dx, dy = 0.0, 0.0
        if len(history) >= 2:
            dt = max(0.001, history[-1][2] - history[0][2])
            dx = (history[-1][0] - history[0][0]) / dt
            dy = (history[-1][1] - history[0][1]) / dt

        speed_px = math.hypot(dx, dy)
        heading_deg = (math.atan2(dy, dx) * 180.0 / math.pi) % 360.0
        cardinals = ["E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N", "NNE", "NE", "ENE"]
        card_idx = int((heading_deg + 11.25) / 22.5) % 16
        cardinal = cardinals[card_idx]

        dist_to_fence = max(20.0, abs((h * 0.85) - cy))
        effective_speed = max(speed_px, 20.0)
        eta_sec = max(18, min(85, int(dist_to_fence / effective_speed * 3.2)))

        heading_str = f"{int(heading_deg)}° {cardinal} ({'Inbound' if dy > 0 else 'Lateral'})"
        sector_idx = (abs(tid) % 6) + 1
        intercept_zone = f"Buffer Zone Sector-{sector_idx} (Post Alpha)"
        return eta_sec, heading_str, intercept_zone

    def process(
        self,
        frame: Frame,
        t1_dets: List[Detection],
        t3_dets: List[Detection],
        tracked_dets: List[Detection],
        boundary_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        is_night: bool = False,
    ) -> List[Alert]:
        alerts: List[Alert] = []
        now_ts = datetime.now(timezone.utc)
        now_sec = time.time()
        h, w = frame.img.shape[:2]

        if boundary_line:
            self.virtual_fence.tripwire_line = boundary_line

        # When no one / no tracked entity is present, exit immediately (zero alerts, zero false beeps)
        if not tracked_dets:
            return []

        # ------------------------------------------------------------------
        # 1. Facial Recognition System (FRS) & Face Detection
        # ------------------------------------------------------------------
        face_events = self.face_detector.process_person_detections(frame.img, tracked_dets)
        for fe in face_events:
            tid = fe["track_id"]
            name = fe["face_name"]
            conf = fe.get("confidence_pct", 85)
            matched_photo = fe.get("matched_photo")
            key = f"frs_{tid}_{name}"
            if self._should_emit(key, cooldown_seconds=4.0):
                prio = AlertPriority.RED if fe["priority"] == "RED" else AlertPriority.AMBER
                desc = f"FRS Suspect Confirmed: {name} ({conf}% Match) - {fe.get('notes', 'Flagged Suspect')}"
                thumb_b64 = self._extract_crop_b64(frame.img, fe["bbox"])
                p_eta, p_heading, p_zone = self._compute_predictive_vector(tid, fe["bbox"], (h, w))

                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="Facial Recognition & Known Entities",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.FACE_RECOGNITION,
                    priority=prio,
                    description=desc,
                    bboxes=[BoundingBox(x1=fe["bbox"][0], y1=fe["bbox"][1], x2=fe["bbox"][2], y2=fe["bbox"][3])],
                    track_ids=[tid] if tid is not None else [],
                    face_name=name,
                    snapshot_b64=thumb_b64,
                    predictive_eta_sec=p_eta,
                    predictive_heading=p_heading,
                    intercept_sector=p_zone,
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.FACE_RECOGNITION.value,
                    priority=prio.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                    face_name=name,
                    track_id=tid,
                    snapshot_b64=thumb_b64,
                )

        # ------------------------------------------------------------------
        # 2. Automatic Number Plate Recognition (ANPR)
        # ------------------------------------------------------------------
        anpr_events = self.anpr_detector.process_vehicle_detections(frame.img, tracked_dets)
        for ae in anpr_events:
            tid = ae["track_id"]
            plate = ae["plate_number"]
            is_susp = ae["is_suspect"]
            v_type = ae["vehicle_type"]
            key = f"anpr_{tid}_{plate}"
            if self._should_emit(key, cooldown_seconds=5.0):
                # Respect configured priority: RED, AMBER, or BLUE (for authorized vehicles)
                assigned_prio = ae.get("priority", "RED" if is_susp else "BLUE").upper()
                if assigned_prio == "RED":
                    prio = AlertPriority.RED
                elif assigned_prio == "AMBER":
                    prio = AlertPriority.AMBER
                else:
                    prio = AlertPriority.BLUE
                desc = f"ANPR License Plate: {plate} [{v_type}] - {ae['reason']}"
                thumb_b64 = self._extract_crop_b64(frame.img, ae["bbox"])

                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="ANPR & Vehicle Identification",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.ANPR_PLATE,
                    priority=prio,
                    description=desc,
                    bboxes=[BoundingBox(x1=ae["bbox"][0], y1=ae["bbox"][1], x2=ae["bbox"][2], y2=ae["bbox"][3])],
                    track_ids=[tid] if tid is not None else [],
                    plate_number=plate,
                    snapshot_b64=thumb_b64,
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.ANPR_PLATE.value,
                    priority=prio.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                    plate_number=plate,
                    track_id=tid,
                    snapshot_b64=thumb_b64,
                )

        has_human = any(d.category == "Person" for d in tracked_dets)
        has_weapon = any(d.category == "Weapon" for d in tracked_dets)

        # ------------------------------------------------------------------
        # Weapon / Knife / Armed Threat Detection
        # ------------------------------------------------------------------
        weapon_dets = [d for d in tracked_dets if d.category == "Weapon"]
        for wd in weapon_dets:
            w_type = wd.sub_category or "Weapon"
            tid = wd.track_id or 0
            key = f"weapon_{tid}_{w_type}"
            if self._should_emit(key, cooldown_seconds=3.0):
                desc = f"CRITICAL ARMED THREAT: {w_type} detected in border sector!"
                thumb_b64 = self._extract_crop_b64(frame.img, wd.bbox)
                p_eta, p_heading, p_zone = self._compute_predictive_vector(tid, wd.bbox, (h, w))
                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="Weapons & Armed Threat Interception",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.WEAPON,
                    priority=AlertPriority.RED,
                    description=desc,
                    bboxes=[BoundingBox(x1=wd.bbox[0], y1=wd.bbox[1], x2=wd.bbox[2], y2=wd.bbox[3])],
                    track_ids=[tid] if tid else [],
                    snapshot_b64=thumb_b64,
                    predictive_eta_sec=p_eta,
                    predictive_heading=p_heading,
                    intercept_sector=p_zone,
                )
                alerts.append(alert)
                event_store.log_event(
                    category=AlertCategory.WEAPON.value,
                    priority=AlertPriority.RED.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                    track_id=tid,
                    snapshot_b64=thumb_b64,
                )

        # ------------------------------------------------------------------
        # Entity & Object Identification Recon (Section 1: Person, Animal, Item)
        # ------------------------------------------------------------------
        for det in tracked_dets:
            tid = det.track_id or 0
            if det.category in ["Person", "Animal", "Item"]:
                item_name = det.sub_category or det.category
                key = f"recon_{det.category.lower()}_{tid}_{item_name}"
                if self._should_emit(key, cooldown_seconds=8.0):
                    if det.category == "Person":
                        desc = f"Human Entity Recon: Person tracked in sector (Track #{tid})"
                        prio = AlertPriority.BLUE
                        cat = AlertCategory.PERSON
                    elif det.category == "Animal":
                        desc = f"Wildlife Recon: {item_name} detected in sector (Track #{tid})"
                        prio = AlertPriority.GRAY
                        cat = AlertCategory.ANIMAL
                    else:  # Item
                        desc = f"Item Identification: {item_name} recognized in sector (Track #{tid})"
                        prio = AlertPriority.GRAY
                        cat = AlertCategory.ITEM

                    thumb_b64 = self._extract_crop_b64(frame.img, det.bbox)
                    alert = Alert(
                        timestamp=now_ts,
                        section=1,
                        section_title="Target Recon & Object Intelligence",
                        camera_id=self.camera_id,
                        location=self.location,
                        category=cat,
                        priority=prio,
                        description=desc,
                        bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                        track_ids=[tid] if tid else [],
                        snapshot_b64=thumb_b64,
                    )
                    alerts.append(alert)
                    event_store.log_event(
                        category=cat.value,
                        priority=prio.value,
                        description=desc,
                        camera_id=self.camera_id,
                        location=self.location,
                        track_id=tid,
                        snapshot_b64=thumb_b64,
                    )

        # ------------------------------------------------------------------
        # 3. Infiltration & Virtual Fence Perimeter Intrusion Detection
        # ------------------------------------------------------------------
        breach_events, breached_tids = self.virtual_fence.check_intrusions((h, w), tracked_dets)
        for be in breach_events:
            tid = be["track_id"]
            key = f"vf_breach_{tid}"
            if self._should_emit(key, cooldown_seconds=3.0):
                desc = f"INFILTRATION ALERT: Border boundary breach confirmed by Person #{tid} ({be['reason']})"
                thumb_b64 = self._extract_crop_b64(frame.img, be["bbox"])
                p_eta, p_heading, p_zone = self._compute_predictive_vector(tid, be["bbox"], (h, w))

                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="Infiltration & Border Breaches",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.INFILTRATION,
                    priority=AlertPriority.RED,
                    description=desc,
                    bboxes=[BoundingBox(x1=be["bbox"][0], y1=be["bbox"][1], x2=be["bbox"][2], y2=be["bbox"][3])],
                    track_ids=[tid],
                    is_crossing=True,
                    snapshot_b64=thumb_b64,
                    predictive_eta_sec=p_eta,
                    predictive_heading=p_heading,
                    intercept_sector=p_zone,
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.INFILTRATION.value,
                    priority=AlertPriority.RED.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                    track_id=tid,
                    snapshot_b64=thumb_b64,
                )

        # ------------------------------------------------------------------
        # 4. Suspicious Activity Detection (Loitering / Sprint / Abandoned)
        # ------------------------------------------------------------------
        susp_events = self.suspicious_detector.analyze(tracked_dets, t3_dets)
        for se in susp_events:
            stype = se["type"]
            tid = se.get("track_id") or 0
            key = f"susp_{stype}_{tid}"
            if self._should_emit(key, cooldown_seconds=4.0):
                prio = AlertPriority.RED if se["priority"] == "RED" else AlertPriority.AMBER
                desc = se["description"]
                thumb_b64 = self._extract_crop_b64(frame.img, se["bbox"]) if se.get("bbox") else None

                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="Suspicious Activity & Threat Behavioral Analysis",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.SUSPICIOUS_ACTIVITY,
                    priority=prio,
                    description=desc,
                    bboxes=[BoundingBox(x1=se["bbox"][0], y1=se["bbox"][1], x2=se["bbox"][2], y2=se["bbox"][3])] if se.get("bbox") else [],
                    track_ids=[tid] if tid else [],
                    snapshot_b64=thumb_b64,
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.SUSPICIOUS_ACTIVITY.value,
                    priority=prio.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                    track_id=tid,
                    snapshot_b64=thumb_b64,
                )

        # ------------------------------------------------------------------
        # 5. Night-Time Movement Detection (Only when a person is present)
        # ------------------------------------------------------------------
        if is_night and has_human:
            if self._should_emit("night_movement", cooldown_seconds=6.0):
                person_tids = [d.track_id for d in tracked_dets if d.category == "Person" and d.track_id is not None]
                desc = f"Night Infiltration Risk: Person movement detected under low-light/IR conditions (Track #{', #'.join(str(t) for t in person_tids)})"
                alert = Alert(
                    timestamp=now_ts,
                    section=1,
                    section_title="Night Surveillance & Thermal Vision",
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.NIGHT_MOVEMENT,
                    priority=AlertPriority.AMBER,
                    description=desc,
                    bboxes=[BoundingBox(x1=d.bbox[0], y1=d.bbox[1], x2=d.bbox[2], y2=d.bbox[3]) for d in tracked_dets if d.category == "Person"][:4],
                    track_ids=person_tids[:4],
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.NIGHT_MOVEMENT.value,
                    priority=AlertPriority.AMBER.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                )

        # ------------------------------------------------------------------
        # 6. Aerial Threats & Drones (Strictly verified Drone category only)
        # ------------------------------------------------------------------
        for det in tracked_dets:
            if det.category == "Drone" and det.confidence >= 0.40:
                tid = det.track_id or 0
                if self._should_emit(f"drone_{tid}", cooldown_seconds=4.0):
                    desc = f"Airspace Breach: Verified Drone / UAV Threat intercepted at altitude Y:{int(det.cy)}px (Track #{tid})"
                    thumb_b64 = self._extract_crop_b64(frame.img, det.bbox)
                    alert = Alert(
                        timestamp=now_ts,
                        section=2,
                        section_title=SECTION_TITLES[2],
                        camera_id=self.camera_id,
                        location=self.location,
                        category=AlertCategory.DRONE,
                        priority=AlertPriority.RED,
                        description=desc,
                        bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                        track_ids=[tid],
                        snapshot_b64=thumb_b64,
                    )
                    alerts.append(alert)

                    event_store.log_event(
                        category=AlertCategory.DRONE.value,
                        priority=alert.priority.value,
                        description=desc,
                        camera_id=self.camera_id,
                        location=self.location,
                        track_id=tid,
                        snapshot_b64=thumb_b64,
                    )

        # ------------------------------------------------------------------
        # 7. Mass Incursion & Group Clusters
        # ------------------------------------------------------------------
        active_entities = [d for d in tracked_dets if d.track_id is not None and d.category in ["Person", "Vehicle"]]
        clusters: List[List[Detection]] = []
        assigned = [False] * len(active_entities)

        for i, d1 in enumerate(active_entities):
            if assigned[i]:
                continue
            cluster = [d1]
            assigned[i] = True
            for j, d2 in enumerate(active_entities):
                if assigned[j] or i == j:
                    continue
                dist = np.hypot(d1.cx - d2.cx, d1.cy - d2.cy)
                if dist < 120.0:
                    cluster.append(d2)
                    assigned[j] = True
            if len(cluster) >= 2:
                clusters.append(cluster)

        for cl in clusters:
            n = len(cl)
            tids = [d.track_id for d in cl if d.track_id is not None]
            group_key = f"group_{'_'.join(str(t) for t in sorted(tids))}"
            is_crossing = any(d.track_id in breached_tids for d in cl)

            # Only trigger an alert if there is an actual perimeter crossing breach,
            # or if 4 or more entities gather together (true large congregation).
            # Do NOT sound alarms when 2 normal people are simply standing in front of the camera.
            if not is_crossing and n < 4:
                continue

            if self._should_emit(group_key, cooldown_seconds=5.0):
                if is_crossing:
                    desc = f"Mass Incursion: Group breach across perimeter by {n} entities (Tracks: #{', #'.join(str(t) for t in tids)})"
                    prio = AlertPriority.RED
                else:
                    desc = f"Group Gathering: Cluster of {n} entities detected together in sector (Tracks: #{', #'.join(str(t) for t in tids)})"
                    prio = AlertPriority.AMBER

                alert = Alert(
                    timestamp=now_ts,
                    section=3,
                    section_title=SECTION_TITLES[3],
                    camera_id=self.camera_id,
                    location=self.location,
                    category=AlertCategory.GROUP,
                    priority=prio,
                    description=desc,
                    bboxes=[BoundingBox(x1=d.bbox[0], y1=d.bbox[1], x2=d.bbox[2], y2=d.bbox[3]) for d in cl],
                    track_ids=tids,
                    group_size=n,
                    is_crossing=is_crossing,
                )
                alerts.append(alert)

                event_store.log_event(
                    category=AlertCategory.GROUP.value,
                    priority=alert.priority.value,
                    description=desc,
                    camera_id=self.camera_id,
                    location=self.location,
                )

        # Prune expired cooldowns
        if len(self._alert_cooldowns) > 250:
            self._alert_cooldowns = {k: v for k, v in self._alert_cooldowns.items() if (now_sec - v) < 20.0}

        return alerts
