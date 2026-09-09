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

import logging
from typing import Optional

import numpy as np

from backend.ingestion.frame_model import Detection, Frame

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """
    Lazy-loaded embedding extractor for face (ArcFace) and body (OSNet).
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
            import insightface
            app = insightface.app.FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(160, 160))
            self._arcface = app
            logger.info("[Embedding] ArcFace (InsightFace) loaded.")
        except ImportError:
            logger.warning("[Embedding] insightface not installed. Face embeddings disabled.")
            self._arcface = None
        self._arcface_loaded = True
        return self._arcface is not None

    def _ensure_osnet(self) -> bool:
        if self._osnet_loaded:
            return self._osnet is not None
        try:
            import torchreid
            self._osnet = torchreid.utils.FeatureExtractor(
                model_name="osnet_x0_25",
                device="cpu",
            )
            logger.info("[Embedding] OSNet (torchreid) loaded.")
        except ImportError:
            logger.warning("[Embedding] torchreid not installed. Body embeddings disabled.")
            self._osnet = None
        self._osnet_loaded = True
        return self._osnet is not None

    def extract_face(self, frame: Frame, det: Detection) -> Optional[np.ndarray]:
        """Extract ArcFace embedding from the face region in the bounding box."""
        if not self._ensure_arcface():
            return None
        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        crop = frame.img[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        faces = self._arcface.get(crop)
        if not faces:
            return None
        return faces[0].embedding   # 512-d ArcFace vector

    def extract_body(self, frame: Frame, det: Detection) -> Optional[np.ndarray]:
        """Extract OSNet body appearance embedding from the bounding box crop."""
        if not self._ensure_osnet():
            return None
        import cv2
        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        crop = frame.img[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        features = self._osnet([crop_rgb])
        return features[0].cpu().numpy()

    def extract(self, frame: Frame, det: Detection) -> None:
        """Extract and populate both embeddings in-place on the Detection object."""
        det.face_embedding = self.extract_face(frame, det)
        det.body_embedding = self.extract_body(frame, det)
