"""
backend/detection/face_detector.py
----------------------------------
Face Detection & Facial Recognition System (FRS) for Border Surveillance (IBVAP).

Features:
- Multi-Photo Enrolment: Enrolls multiple reference photos per suspect (front, 45-deg angle, varied lighting).
- Deep Feature Extraction: Extracts normalized facial feature embeddings using MobileNetV3 (with CPU optimization).
- Multi-Angle Matching: Compares live face crops against all enrolled photos per suspect and selects maximum similarity.
- Confirmed Identification: Confirms positive suspect identification with confidence scoring and flags suspect details.
- Dynamic Gallery Reloading: Instantly re-indexes suspect reference photos when updated via dashboard without restarting server.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torchvision.models as models
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from backend.ingestion.frame_model import Detection, Frame

logger = logging.getLogger("FaceDetector")
WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "config" / "watchlist.json"
FACES_DIR = Path(__file__).resolve().parent.parent / "data" / "faces"
FACES_DIR.mkdir(parents=True, exist_ok=True)


class FaceDetector:
    """
    Real-time Multi-Photo Face Detector and Recognition Matcher.
    """

    def __init__(self, watchlist_path: Path = WATCHLIST_PATH):
        self.watchlist_path = Path(watchlist_path)
        self._cascade = None

        # Try loading CascadeClassifier if available in this OpenCV build
        if hasattr(cv2, "CascadeClassifier"):
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                casc = cv2.CascadeClassifier(cascade_path)
                if not casc.empty():
                    self._cascade = casc
                    logger.info("[FaceDetector] OpenCV Face Cascade loaded.")
            except Exception as e:
                logger.debug("[FaceDetector] CascadeClassifier init skipped: %s", e)

        # Initialize Neural Feature Extractor
        self._torch_model = None
        self._transform = None
        if TORCH_AVAILABLE:
            try:
                m = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
                m.classifier = nn.Identity()
                m.eval()
                self._torch_model = m
                self._transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Resize((112, 112)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
                logger.info("[FaceDetector] MobileNetV3 deep facial feature extractor initialized.")
            except Exception as e:
                logger.warning("[FaceDetector] Neural model load fallback to spatial histograms: %s", e)

        # In-memory enrolled suspect gallery:
        # id -> { id, name, priority, notes, photos, embeddings: [np.ndarray, ...] }
        self.gallery: Dict[str, Dict[str, Any]] = {}
        self.watchlist: List[Dict[str, Any]] = []
        self._last_mtime: float = 0.0
        self._track_identities: Dict[int, Dict[str, Any]] = {}  # track_id -> { match, last_seen, last_checked }
        self._civilian_tracks: Dict[int, float] = {}             # track_id -> last_checked_ts
        if TORCH_AVAILABLE:
            try:
                torch.set_num_threads(2)
            except Exception:
                pass
        self.reload_gallery()

    def reload_gallery(self):
        """
        Loads all suspect profiles and extracts multi-condition face embeddings (standard, pose-flipped, CLAHE lighting normalized).
        """
        try:
            if not self.watchlist_path.exists():
                logger.warning("[FaceDetector] Watchlist file not found at %s", self.watchlist_path)
                self.gallery = {}
                self.watchlist = []
                return

            self._last_mtime = self.watchlist_path.stat().st_mtime
            with open(self.watchlist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.watchlist = data.get("suspect_faces", [])

            new_gallery: Dict[str, Dict[str, Any]] = {}
            total_photos_enrolled = 0

            for suspect in self.watchlist:
                sid = suspect.get("id") or f"SUSP_{len(new_gallery)+1}"
                name = suspect.get("name", "Unknown Suspect")
                priority = suspect.get("priority", "RED")
                notes = suspect.get("notes", "")
                photos = suspect.get("photos", [])

                embeddings: List[np.ndarray] = []
                for p_ref in photos:
                    img = self._load_photo_image(p_ref)
                    if img is not None and img.size > 0:
                        # 1. Primary pure face ROI crop embedding
                        face_crop = self._extract_face_roi_from_photo(img)
                        emb = self.extract_embedding(face_crop)
                        if emb is not None:
                            embeddings.append(emb)
                            total_photos_enrolled += 1

                        # 2. Horizontal-flipped face embedding (provides pose & viewing-angle invariance)
                        try:
                            flipped_face = cv2.flip(face_crop, 1)
                            emb_flip = self.extract_embedding(flipped_face)
                            if emb_flip is not None:
                                embeddings.append(emb_flip)
                        except Exception:
                            pass

                        # 3. CLAHE Lighting-normalized face embedding (shadow & brightness invariant)
                        try:
                            lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
                            l, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
                            l_eq = clahe.apply(l)
                            norm_crop = cv2.cvtColor(cv2.merge((l_eq, a, b)), cv2.COLOR_LAB2BGR)
                            emb_light = self.extract_embedding(norm_crop)
                            if emb_light is not None:
                                embeddings.append(emb_light)
                        except Exception:
                            pass

                new_gallery[sid] = {
                    "id": sid,
                    "name": name,
                    "priority": priority,
                    "notes": notes,
                    "photos": photos,
                    "embeddings": embeddings,
                }

            self.gallery = new_gallery
            self._track_identities.clear()
            self._civilian_tracks.clear()
            logger.info(
                "[FaceDetector] Watchlist synced: %d suspect profiles indexed (%d embeddings ready).",
                len(self.gallery),
                total_photos_enrolled,
            )
        except Exception as e:
            logger.error("[FaceDetector] Failed to reload gallery: %s", e)

    def _load_photo_image(self, p_ref: str) -> Optional[np.ndarray]:
        """Load image from URL path, disk path, or base64 data."""
        try:
            if not p_ref:
                return None

            # 1. Base64 Data URI
            if p_ref.startswith("data:image"):
                b64_part = p_ref.split(",", 1)[1]
                data = base64.b64decode(b64_part)
                arr = np.frombuffer(data, dtype=np.uint8)
                return cv2.imdecode(arr, cv2.IMREAD_COLOR)

            # 2. API face path e.g. "/api/faces/xxx.jpg"
            if p_ref.startswith("/api/faces/"):
                fname = p_ref.replace("/api/faces/", "")
                fpath = FACES_DIR / fname
                if fpath.exists():
                    return cv2.imread(str(fpath))

            # 3. Direct disk path
            p = Path(p_ref)
            if p.exists():
                return cv2.imread(str(p))

            # 4. Check FACES_DIR by filename
            cand = FACES_DIR / p.name
            if cand.exists():
                return cv2.imread(str(cand))
        except Exception as e:
            logger.debug("[FaceDetector] Failed to load photo reference '%s': %s", p_ref, e)
        return None

    def _extract_face_roi_from_photo(self, img: np.ndarray) -> np.ndarray:
        """Find face ROI inside enrolled photo or return whole photo if cropped."""
        h, w = img.shape[:2]
        if h < 40 or w < 40:
            return img
        face_rect = self._locate_face_in_head(img)
        if face_rect is not None:
            fx, fy, fw, fh = face_rect
            fx1 = max(0, fx - int(fw * 0.1))
            fy1 = max(0, fy - int(fh * 0.1))
            fx2 = min(w, fx + fw + int(fw * 0.1))
            fy2 = min(h, fy + fh + int(fh * 0.1))
            crop = img[fy1:fy2, fx1:fx2]
            if crop.size > 200:
                return crop
        return img

    def _locate_face_in_head(self, head_crop: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Locate face bounding box in head ROI using cascade or skin-tone morphology.
        """
        hh, hw = head_crop.shape[:2]
        if hh < 15 or hw < 15:
            return None

        # 1. Try cascade if available
        if self._cascade is not None:
            gray = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
            faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(16, 16))
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                return (fx, fy, fw, fh)

        # 2. Robust Skin-Tone Ellipse Localization (OpenCV 5.0+ Native)
        ycrcb = cv2.cvtColor(head_crop, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 40:
                bx, by, bw, bh = cv2.boundingRect(c)
                return (max(0, bx - 2), max(0, by - 2), min(hw - bx, bw + 4), min(hh - by, bh + 4))

        # 3. Default central head region heuristic
        margin_x = int(hw * 0.15)
        margin_y = int(hh * 0.10)
        return (margin_x, margin_y, int(hw * 0.70), int(hh * 0.75))

    def extract_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Extract a normalized unit embedding vector for the face crop.
        """
        if face_crop is None or face_crop.size == 0:
            return np.zeros(576, dtype=np.float32)

        # 1. Neural MobileNetV3 extraction (primary)
        if self._torch_model is not None and self._transform is not None:
            try:
                rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                tensor = self._transform(rgb).unsqueeze(0)
                with torch.no_grad():
                    feat = self._torch_model(tensor).squeeze().cpu().numpy()
                norm = np.linalg.norm(feat)
                if norm > 1e-6:
                    return (feat / norm).astype(np.float32)
            except Exception as e:
                logger.debug("[FaceDetector] Neural embedding failed, fallback to spatial hist: %s", e)

        # 2. Multi-Scale Spatial Grid + Gradient Histogram Fallback
        norm_face = cv2.resize(face_crop, (96, 96))
        gray = cv2.cvtColor(norm_face, cv2.COLOR_BGR2GRAY) if len(norm_face.shape) == 3 else norm_face
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        gray_eq = clahe.apply(gray)

        # 4x4 spatial blocks
        bh, bw = 24, 24
        feats = []
        for r in range(4):
            for c in range(4):
                blk = gray_eq[r * bh : (r + 1) * bh, c * bw : (c + 1) * bw]
                h = cv2.calcHist([blk], [0], None, [16], [0, 256]).flatten()
                norm = np.linalg.norm(h)
                feats.append(h / (norm + 1e-6))

        # Directional gradients
        gx = cv2.Sobel(gray_eq, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_eq, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        ang_bins = ((ang / 45.0).astype(np.int32)) % 8
        for r in range(4):
            for c in range(4):
                b_ang = ang_bins[r * bh : (r + 1) * bh, c * bw : (c + 1) * bw]
                b_mag = mag[r * bh : (r + 1) * bh, c * bw : (c + 1) * bw]
                b_hist = np.zeros(8, dtype=np.float32)
                for b in range(8):
                    b_hist[b] = np.sum(b_mag[b_ang == b])
                feats.append(b_hist / (np.linalg.norm(b_hist) + 1e-6))

        tot = np.concatenate(feats).astype(np.float32)
        norm_tot = np.linalg.norm(tot)
        return tot / (norm_tot + 1e-6)

    def match_face(self, face_crop: np.ndarray, threshold: float = 0.78) -> Optional[Dict[str, Any]]:
        """
        Compares live face/person crop against all enrolled photos of all suspects.
        Returns matched suspect details if similarity exceeds threshold (default: 0.78).
        """
        if not self.gallery or face_crop is None or face_crop.size == 0:
            return None

        live_emb = self.extract_embedding(face_crop)
        if live_emb is None:
            return None

        best_suspect = None
        best_sim = -1.0
        best_photo_url = None

        for sid, suspect in self.gallery.items():
            embs = suspect.get("embeddings", [])
            if not embs:
                continue

            # Compare against all enrolled embeddings for this suspect
            sims = [float(np.dot(live_emb, ref_emb)) for ref_emb in embs]
            s_max = max(sims)
            s_idx = sims.index(s_max)

            if s_max > best_sim:
                best_sim = s_max
                best_suspect = suspect
                photos = suspect.get("photos", [])
                best_photo_url = photos[s_idx % len(photos)] if photos else None

        if best_suspect is not None and best_sim >= threshold:
            # Calibrate similarity to intuitive confidence percentage [80% - 99%]
            conf_pct = min(99, max(80, int((best_sim - 0.75) / (1.0 - 0.75) * 19 + 80)))
            return {
                "matched": True,
                "id": best_suspect["id"],
                "name": best_suspect["name"],
                "priority": best_suspect.get("priority", "RED"),
                "notes": best_suspect.get("notes", "Matched against enrolled suspect photos"),
                "confidence": round(best_sim, 3),
                "confidence_pct": conf_pct,
                "matched_photo": best_photo_url,
            }

        return None

    def process_person_detections(
        self,
        frame_img: np.ndarray,
        person_detections: List[Detection],
    ) -> List[Dict[str, Any]]:
        """
        Processes human detections, extracts facial regions, performs watchlist matching,
        and strictly enforces 1-to-1 frame uniqueness so multiple people in view are NEVER
        falsely all labeled as the same watchlist suspect.
        """
        # 0. Live Watchlist Disk Sync Check
        try:
            if self.watchlist_path.exists():
                mtime = self.watchlist_path.stat().st_mtime
                if mtime > self._last_mtime:
                    logger.info("[FaceDetector] Watchlist file modified (mtime: %s). Auto-syncing facial gallery...", mtime)
                    self.reload_gallery()
        except Exception as e:
            logger.debug("[FaceDetector] Watchlist sync check skipped: %s", e)

        if frame_img is None:
            return []

        h, w = frame_img.shape[:2]
        now = time.time()

        # If gallery is empty, label everyone as unflagged civilian and return
        if not self.gallery:
            for det in person_detections:
                if det.category == "Person":
                    x1, y1, x2, y2 = [int(v) for v in det.bbox]
                    face_box_y2 = min(h, y1 + int((y2 - y1) * 0.35))
                    det.face_detected = True
                    det.face_bbox = (float(x1), float(y1), float(x2), float(face_box_y2))
                    det.is_watchlist_match = False
                    det.suspect_name = None
                    det.face_name = "Subject (Unflagged)"
            return []

        # Clean up stale track continuity records (> 3.5 seconds old)
        stale_tracks = [t for t, v in self._track_identities.items() if (now - v.get("last_seen", 0)) > 3.5]
        for t in stale_tracks:
            self._track_identities.pop(t, None)
        stale_civs = [t for t, ts in self._civilian_tracks.items() if (now - ts) > 3.5]
        for t in stale_civs:
            self._civilian_tracks.pop(t, None)

        face_events = []
        candidates_pool = []

        for det in person_detections:
            if det.category != "Person":
                continue

            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            pw, ph = x2 - x1, y2 - y1
            if pw < 15 or ph < 20:
                continue

            face_box_y2 = min(h, y1 + int(ph * 0.35))
            det.face_detected = True
            det.face_bbox = (float(x1), float(y1), float(x2), float(face_box_y2))

            # FAST TRACK-CONTINUITY BYPASS:
            # 1. Active unflagged civilian cache (verify periodically instead of heavy deep pass every single frame)
            if det.track_id is not None and det.track_id in self._civilian_tracks:
                if (now - self._civilian_tracks[det.track_id]) < 0.8:
                    det.is_watchlist_match = False
                    det.suspect_name = None
                    det.face_name = "Subject (Unflagged)"
                    continue

            # 2. Confirmed suspect track cache (verify periodically while maintaining stable alert)
            if det.track_id is not None and det.track_id in self._track_identities:
                prev = self._track_identities[det.track_id]
                if (now - prev.get("last_checked", 0)) < 0.5:
                    prev["last_seen"] = now
                    match = prev["match"]
                    det.is_watchlist_match = True
                    det.suspect_name = match["name"]
                    det.face_name = f"{match['name']} ({match['confidence_pct']}%)"
                    face_events.append({
                        "track_id": det.track_id,
                        "suspect_id": match["id"],
                        "face_name": match["name"],
                        "confidence_pct": match["confidence_pct"],
                        "priority": match["priority"],
                        "notes": match["notes"],
                        "matched_photo": match.get("matched_photo"),
                        "bbox": det.face_bbox,
                    })
                    continue

            # Candidate scale crops strictly focused on the face / head region:
            head_h = max(20, int(ph * 0.38))
            head_crop = frame_img[y1:min(h, y1 + head_h), x1:x2]

            face_roi = None
            face_rect = self._locate_face_in_head(head_crop)
            if face_rect is not None:
                fx, fy, fw, fh = face_rect
                face_roi = head_crop[fy:fy+fh, fx:fx+fw]

            candidates = []
            if face_roi is not None and face_roi.size > 100:
                candidates.append(face_roi)
            if head_crop is not None and head_crop.size > 100:
                candidates.append(head_crop)

            upper_h = min(h, y1 + int(ph * 0.70))
            if upper_h > y1 + 30:
                upper_crop = frame_img[y1:upper_h, x1:x2]
                if upper_crop.size > 100:
                    candidates.append(upper_crop)

            full_crop = frame_img[y1:y2, x1:x2]
            if full_crop.size > 100:
                candidates.append(full_crop)

            best_match = None
            best_sim = -1.0
            for cand in candidates:
                m = self.match_face(cand, threshold=0.78)
                if m and m["confidence"] > best_sim:
                    best_sim = m["confidence"]
                    best_match = m
                    # SPEED BOOST: If high-confidence match found, stop evaluating remaining crops!
                    if m["confidence"] >= 0.82:
                        break

            # Track identity continuity smoothing (anti-flicker on head turns/tilt)
            if (best_match is None or best_sim < 0.78) and det.track_id is not None:
                prev = self._track_identities.get(det.track_id)
                if prev and (now - prev.get("last_seen", 0)) < 2.5:
                    best_match = prev["match"]
                    best_sim = 0.79

            candidates_pool.append({
                "det": det,
                "match": best_match,
                "sim": best_sim,
            })

        # 1-to-1 Frame Uniqueness Constraint:
        # Sort candidate matches by similarity descending so the single best physical match wins
        candidates_pool.sort(key=lambda item: item["sim"], reverse=True)
        assigned_suspect_ids = set()

        for item in candidates_pool:
            det = item["det"]
            match = item["match"]
            sim = item["sim"]

            if match and match["id"] not in assigned_suspect_ids and sim >= 0.78:
                assigned_suspect_ids.add(match["id"])
                det.is_watchlist_match = True
                det.suspect_name = match["name"]
                det.face_name = f"{match['name']} ({match['confidence_pct']}%)"

                # Update or register track identity continuity
                if det.track_id is not None:
                    self._track_identities[det.track_id] = {
                        "match": match,
                        "last_seen": now,
                        "last_checked": now,
                    }
                    self._civilian_tracks.pop(det.track_id, None)

                face_events.append({
                    "track_id": det.track_id,
                    "suspect_id": match["id"],
                    "face_name": match["name"],
                    "confidence_pct": match["confidence_pct"],
                    "priority": match["priority"],
                    "notes": match["notes"],
                    "matched_photo": match.get("matched_photo"),
                    "bbox": det.face_bbox,
                })
            else:
                # All other people remain unflagged civilian subjects without false alarms
                det.is_watchlist_match = False
                det.suspect_name = None
                det.face_name = "Subject (Unflagged)"
                if det.track_id is not None:
                    self._civilian_tracks[det.track_id] = now
                    if sim < 0.70:
                        self._track_identities.pop(det.track_id, None)

        return face_events
