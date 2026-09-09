"""
backend/detection/visualizer.py
--------------------------------
Visualizer for IBVAP (Intelligent Border Video Analytics Platform).

Annotates video streams with:
  - High-precision entity bounding boxes and track IDs
  - Explicit vehicle classification (Car, Truck, Bus, Motorcycle, Bicycle)
  - Face Recognition System (FRS) face bounding boxes and identity tags
  - Automatic Number Plate Recognition (ANPR) license plate tags
  - Virtual Fence perimeter lines (armed / breach glow states)
  - Suspicious activity indicators (loitering duration, incursion speed)
  - C4ISR tactical HUD overlays
"""

from __future__ import annotations

import time
from typing import List, Optional, Set, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame

# BGR color scheme
COLOR_PERSON = (0, 220, 0)         # Green
COLOR_VEHICLE = (240, 120, 0)      # Deep Blue/Cyan
COLOR_ANIMAL = (0, 215, 255)       # Yellow/Amber
COLOR_DRONE = (0, 0, 255)          # Red
COLOR_LUGGAGE = (180, 0, 220)      # Purple
COLOR_UNIDENTIFIED = (180, 180, 180)# Gray
COLOR_FACE = (255, 255, 0)         # Cyan
COLOR_PLATE = (0, 230, 255)        # Bright Yellow
COLOR_CROSSING = (0, 69, 255)      # Orange-Red
COLOR_SAFE_FENCE = (0, 220, 100)   # Emerald Green
COLOR_BREACH_FENCE = (0, 0, 255)   # Red
COLOR_WEAPON = (0, 0, 255)         # Threat Red

CATEGORY_COLORS = {
    "Person": COLOR_PERSON,
    "Weapon": COLOR_WEAPON,
    "Vehicle": COLOR_VEHICLE,
    "Animal": COLOR_ANIMAL,
    "Drone": COLOR_DRONE,
    "Luggage": COLOR_LUGGAGE,
    "Unidentified": COLOR_UNIDENTIFIED,
}


def draw_detections(
    frame: Frame,
    detections: List[Detection],
    boundary_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    perimeter_polygon: Optional[List[Tuple[int, int]]] = None,
    crossing_ids: Optional[Set[int]] = None,
    show_tier: bool = False,
    is_night: bool = False,
) -> np.ndarray:
    """
    Annotates the video frame with tactical AI analytics overlays.
    """
    img = frame.img.copy()
    crossing_ids = crossing_ids or set()
    h, w = img.shape[:2]
    now = time.time()

    # 1. Virtual Fence / Perimeter Overlay
    has_breach = len(crossing_ids) > 0
    fence_color = COLOR_BREACH_FENCE if has_breach else COLOR_SAFE_FENCE

    # Draw polygonal perimeter if defined
    if perimeter_polygon and len(perimeter_polygon) >= 3:
        pts = np.array(perimeter_polygon, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], isClosed=True, color=fence_color, thickness=2, lineType=cv2.LINE_AA)
        status_txt = "VIRTUAL PERIMETER: BREACH DETECTED!" if has_breach else "VIRTUAL PERIMETER: ARMED"
        cv2.putText(
            img, status_txt,
            (perimeter_polygon[0][0], max(20, perimeter_polygon[0][1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, fence_color, 1, cv2.LINE_AA
        )

    # Draw virtual tripwire line
    if boundary_line is not None:
        pt1, pt2 = boundary_line
        cv2.line(img, pt1, pt2, fence_color, 2, cv2.LINE_AA)
        fence_label = "VIRTUAL FENCE: INTRUSION ACTIVE" if has_breach else "VIRTUAL FENCE: ARMED"
        cv2.putText(
            img, fence_label,
            (pt1[0] + 10, max(25, pt1[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, fence_color, 1, cv2.LINE_AA
        )

    # 2. Render Detection Bounding Boxes & AI Badges
    for det in detections:
        if det.suppressed:
            continue

        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        is_breaching = det.track_id is not None and det.track_id in crossing_ids

        is_suspect_match = bool(
            getattr(det, "is_watchlist_match", False) and
            det.face_name and
            "Unflagged" not in det.face_name
        )

        # Main box color
        if is_suspect_match:
            base_color = (0, 0, 255)  # Bright Red for Watchlist Suspect
        elif is_breaching:
            base_color = COLOR_CROSSING
        else:
            base_color = CATEGORY_COLORS.get(det.category, (200, 200, 200))

        cv2.rectangle(img, (x1, y1), (x2, y2), base_color, 3 if is_suspect_match else 2)

        # Primary label (includes Watchlist/Weapon/Vehicle classification)
        cat_label = det.category
        if is_suspect_match:
            s_name = getattr(det, "suspect_name", None) or det.face_name
            cat_label = f"WATCHLIST: {s_name}"
        elif det.category == "Weapon":
            cat_label = f"WEAPON: {det.sub_category or 'Armed Threat'}"
        elif det.category == "Drone":
            cat_label = f"AIR THREAT: {det.sub_category or 'Drone / UAV'}"
        elif det.category == "Vehicle" and det.sub_category:
            cat_label = f"Vehicle ({det.sub_category})"
        elif det.sub_category and det.category in ["Animal", "Luggage"]:
            cat_label = det.sub_category

        label_parts = [cat_label]
        if det.track_id is not None:
            label_parts.append(f"#{det.track_id}")
        label_parts.append(f"{det.confidence:.2f}")
        main_label = " ".join(label_parts)

        # Label background pill
        (tw, th), _ = cv2.getTextSize(main_label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(img, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), base_color, -1)
        cv2.putText(
            img, main_label,
            (x1 + 3, max(th + 2, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
        )

        # Altitude / Vector tag for Aerial Threats
        if det.category == "Drone":
            alt_txt = f"ALT: Y={int(det.cy)}px"
            (atw, ath), _ = cv2.getTextSize(alt_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            cv2.rectangle(img, (x1, y2 + 2), (x1 + atw + 6, y2 + ath + 6), (0, 0, 180), -1)
            cv2.putText(
                img, alt_txt,
                (x1 + 3, y2 + ath + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1, cv2.LINE_AA
            )

        # 3. Face Detection & FRS Overlay
        if det.face_detected and det.face_bbox:
            fx1, fy1, fx2, fy2 = (int(v) for v in det.face_bbox)
            is_suspect_match = det.face_name and "%" in det.face_name and "Unflagged" not in det.face_name
            face_color = (0, 0, 255) if is_suspect_match else (255, 200, 0)
            thickness = 2 if is_suspect_match else 1
            cv2.rectangle(img, (fx1, fy1), (fx2, fy2), face_color, thickness, cv2.LINE_AA)
            if det.face_name and "Unflagged" not in det.face_name:
                face_tag = f"FRS MATCH: {det.face_name}"
                (ftw, fth), _ = cv2.getTextSize(face_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                banner_top = max(0, fy1 - fth - 6)
                cv2.rectangle(img, (fx1, banner_top), (fx1 + ftw + 8, fy1), (0, 0, 180), -1)
                cv2.rectangle(img, (fx1, banner_top), (fx1 + ftw + 8, fy1), (0, 0, 255), 1)
                cv2.putText(
                    img, face_tag,
                    (fx1 + 4, fy1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA
                )

        # 4. ANPR License Plate Badge Overlay
        if det.plate_number:
            plate_tag = f"ANPR: {det.plate_number}"
            (ptw, pth), _ = cv2.getTextSize(plate_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            # Render plate banner at bottom of vehicle bbox
            banner_y = min(h - 5, y2 + pth + 4)
            cv2.rectangle(img, (x1, y2 - 2), (x1 + ptw + 8, banner_y), (0, 0, 0), -1)
            cv2.rectangle(img, (x1, y2 - 2), (x1 + ptw + 8, banner_y), COLOR_PLATE, 1)
            cv2.putText(
                img, plate_tag,
                (x1 + 4, banner_y - 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_PLATE, 1, cv2.LINE_AA
            )

        # 5. Suspicious Loitering Badge
        if det.is_loitering:
            loiter_text = f"LOITERING {int(det.loitering_seconds)}s"
            (ltw, lth), _ = cv2.getTextSize(loiter_text, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.rectangle(img, (x2 - ltw - 6, y1), (x2, y1 + lth + 6), (0, 0, 200), -1)
            cv2.putText(
                img, loiter_text,
                (x2 - ltw - 3, y1 + lth + 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA
            )

    # 6. IBVAP Tactical Header HUD
    hud_bg_w = min(w, 420)
    cv2.rectangle(img, (0, 0), (hud_bg_w, 28), (15, 23, 42), -1)
    cv2.line(img, (0, 28), (hud_bg_w, 28), (51, 65, 85), 1)

    hud_title = f"IBVAP | {frame.camera_id} | {frame.location}"
    cv2.putText(img, hud_title, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (241, 245, 249), 1, cv2.LINE_AA)

    # Mode Indicator badge (Right side)
    mode_str = "NIGHT-VISION (CLAHE)" if is_night else "DAYLIGHT RGB"
    mode_color = (0, 255, 255) if is_night else (100, 255, 100)
    cv2.putText(img, mode_str, (w - 170, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.42, mode_color, 1, cv2.LINE_AA)

    return img


def encode_jpeg(img: np.ndarray, quality: int = 70) -> bytes:
    """Encode a BGR numpy array as JPEG bytes for WebSocket streaming."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buf.tobytes()
