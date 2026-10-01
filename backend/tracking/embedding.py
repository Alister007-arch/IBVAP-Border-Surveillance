"""
backend/tracking/embedding.py
------------------------------
Face + body appearance embedding extraction.

Computes embeddings ONLY:
  - When a new track_id first appears in the camera (new entity entry)
  - Just before the track is expected to exit the frame (pre-exit)

This "compute on demand" strategy keeps CPU/GPU usage proportional to the
number of entity appearances, not the frame rate.

Phase: 5
"""

from __future__ import annotations

import importlib
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """
    Lazy-loaded embedding extractor for face (ArcFace) and body (OSNet),
    with fast robust fallbacks when neural biometrics packages are unavailable.
    """

    def __init__(self):
        self._arcface = None
        self._osnet = None
        self._arcface_loaded = False
        self._osnet_loaded = False

    def _ensure_arcface(self) -> bool:
        if self._arcface_loaded:
            return self._arcface is not None
        try:
            insightface = importlib.import_module("insightface")
            app = insightface.app.FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(160, 160))
            self._arcface = app
            logger.info("[Embedding] ArcFace (InsightFace) loaded.")
        except Exception:
            logger.debug("[Embedding] insightface not available. Using fast appearance fallback for faces.")
            self._arcface = None
        self._arcface_loaded = True
        return self._arcface is not None

    def _ensure_osnet(self) -> bool:
        if self._osnet_loaded:
            return self._osnet is not None
        try:
            torchreid = importlib.import_module("torchreid")
            self._osnet = torchreid.utils.FeatureExtractor(
                model_name="osnet_x0_25",
                device="cpu",
            )
            logger.info("[Embedding] OSNet (torchreid) loaded.")
        except Exception:
            logger.debug("[Embedding] torchreid not available. Using fast appearance fallback for bodies.")
            self._osnet = None
        self._osnet_loaded = True
        return self._osnet is not None

    @staticmethod
    def _safe_crop(img: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """Safely crop an ROI with boundary clamping to avoid empty slices or bounds errors."""
        if img is None or img.size == 0:
            return None
        h, w = img.shape[:2]
        x1, y1, x2, y2 = (round(v) for v in bbox)
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(x1 + 1, min(w, x2))
        y2 = max(y1 + 1, min(h, y2))
        if (x2 - x1) < 8 or (y2 - y1) < 8:
            return None
        crop = img[y1:y2, x1:x2]
        return crop if crop.size > 0 else None

    @staticmethod
    def _fallback_embedding(crop: np.ndarray, dim: int = 512) -> np.ndarray:
        """
        Fast, robust color-spatial histogram descriptor (L2-normalized)
        to preserve Re-ID and tracking matching even without heavy neural weights.
        """
        resized = cv2.resize(crop, (64, 128))
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [64], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [64], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [64], [0, 256])
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        hist_g = cv2.calcHist([mag], [0], None, [64], [0, 256])

        combined = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten(), hist_g.flatten()])
        if len(combined) < dim:
            combined = np.pad(combined, (0, dim - len(combined)), mode="constant")
        else:
            combined = combined[:dim]

        norm = np.linalg.norm(combined)
        if norm > 1e-6:
            combined = combined / norm
        return combined.astype(np.float32)

    def extract_face(self, frame: Frame, det: Detection) -> Optional[np.ndarray]:
        """Extract ArcFace embedding or fallback from the face region."""
        crop = self._safe_crop(frame.img, det.bbox)
        if crop is None:
            return None

        # 1. Neural ArcFace
        if self._ensure_arcface() and self._arcface is not None:
            try:
                faces = self._arcface.get(crop)
                if faces and hasattr(faces[0], "embedding"):
                    emb = faces[0].embedding
                    norm = np.linalg.norm(emb)
                    return (emb / norm).astype(np.float32) if norm > 1e-6 else emb.astype(np.float32)
            except Exception as e:
                logger.debug("[Embedding] ArcFace inference failed: %s", e)

        # 2. Appearance fallback for face crop (top 35% of person)
        fh = max(10, int(crop.shape[0] * 0.35))
        face_crop = crop[:fh, :]
        return self._fallback_embedding(face_crop, dim=512)

    def extract_body(self, frame: Frame, det: Detection) -> Optional[np.ndarray]:
        """Extract OSNet body embedding or fallback from the person bounding box."""
        crop = self._safe_crop(frame.img, det.bbox)
        if crop is None:
            return None

        # 1. Neural OSNet Re-ID
        if self._ensure_osnet() and self._osnet is not None:
            try:
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                features = self._osnet([crop_rgb])
                emb = features[0].cpu().numpy().flatten()
                norm = np.linalg.norm(emb)
                return (emb / norm).astype(np.float32) if norm > 1e-6 else emb.astype(np.float32)
            except Exception as e:
                logger.debug("[Embedding] OSNet inference failed: %s", e)

        # 2. Appearance fallback
        return self._fallback_embedding(crop, dim=512)

    def extract(self, frame: Frame, det: Detection) -> None:
        """Extract and populate both embeddings in-place on the Detection object."""
        det.face_embedding = self.extract_face(frame, det)
        det.body_embedding = self.extract_body(frame, det)

