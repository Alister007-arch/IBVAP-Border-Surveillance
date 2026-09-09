"""
backend/reid/matcher.py
------------------------
Cross-camera re-identification using topology-based handoff.

Logic:
  1. When a track exits a camera's frame, its embedding is stored in a
     rolling gallery with a TTL (time-to-live).
  2. When a new track appears in a *topologically adjacent* camera
     within the expected travel-time window, its embedding is compared
     against all gallery entries from neighbouring cameras.
  3. If cosine similarity exceeds the threshold, the same global_id is
     assigned, creating a persistent cross-camera identity.

Phase: 5
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.config.settings import settings

logger = logging.getLogger(__name__)

ADJACENCY_MAP_PATH = Path(__file__).parent.parent / "config" / "adjacency_map.json"


class CrossCameraReIDMatcher:
    """
    Topology-aware cross-camera re-identification matcher.

    Call `register_exit(camera_id, track_id, embedding)` when a track leaves.
    Call `match(camera_id, embedding)` when a new track appears in a camera.
    """

    def __init__(self, adjacency_path: Path = ADJACENCY_MAP_PATH):
        self._adjacency: Dict[str, List[dict]] = {}
        self._gallery: Dict[str, List[dict]] = {}   # camera_id → list of gallery entries
        self._global_id_counter = 0
        self._load_adjacency(adjacency_path)
        logger.info("[ReID] Cross-camera matcher initialised. Cameras with adjacency: %s",
                    list(self._adjacency.keys()))

    def _load_adjacency(self, path: Path) -> None:
        try:
            with open(path) as f:
                data = json.load(f)
            self._adjacency = data.get("adjacency", {})
        except FileNotFoundError:
            logger.warning("[ReID] adjacency_map.json not found at %s. Cross-camera handoff disabled.", path)

    def _next_global_id(self) -> str:
        self._global_id_counter += 1
        return f"G{self._global_id_counter:04d}"

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def register_exit(
        self,
        camera_id: str,
        track_id: int,
        embedding: np.ndarray,
        global_id: Optional[str] = None,
    ) -> None:
        """
        Store an exiting track's embedding in the gallery.
        Called by the tracking layer when a track is lost/exits frame.
        """
        if embedding is None:
            return
        if camera_id not in self._gallery:
            self._gallery[camera_id] = []

        gid = global_id or self._next_global_id()
        self._gallery[camera_id].append({
            "track_id": track_id,
            "global_id": gid,
            "embedding": embedding,
            "exit_time": time.time(),
            "camera_id": camera_id,
        })
        logger.debug("[ReID] Registered exit %s#%d as %s", camera_id, track_id, gid)

    def match(
        self,
        camera_id: str,
        embedding: np.ndarray,
    ) -> Optional[str]:
        """
        Attempt to match a newly-appeared embedding against the gallery
        of topologically adjacent cameras.

        Returns the matched global_id, or None if no match found.
        """
        if embedding is None:
            return None

        neighbours = self._adjacency.get(camera_id, [])
        now = time.time()
        threshold = settings.reid.embedding_cosine_threshold
        best_gid: Optional[str] = None
        best_sim: float = -1.0

        for neighbor_cfg in neighbours:
            neighbor_id = neighbor_cfg["neighbor"]
            t_min = neighbor_cfg.get("travel_time_min_sec", 0)
            t_max = neighbor_cfg.get("travel_time_max_sec", 300)

            for entry in self._gallery.get(neighbor_id, []):
                age = now - entry["exit_time"]
                if age < t_min or age > t_max:
                    continue   # outside the expected travel-time window

                sim = self._cosine_similarity(embedding, entry["embedding"])
                if sim > threshold and sim > best_sim:
                    best_sim = sim
                    best_gid = entry["global_id"]

        if best_gid:
            logger.info(
                "[ReID] New track in %s matched to %s (similarity %.3f)",
                camera_id, best_gid, best_sim,
            )
        return best_gid

    def prune_gallery(self) -> None:
        """Remove expired gallery entries (older than gallery_ttl_seconds)."""
        ttl = settings.reid.gallery_ttl_seconds
        now = time.time()
        for cam in list(self._gallery.keys()):
            self._gallery[cam] = [
                e for e in self._gallery[cam]
                if now - e["exit_time"] < ttl
            ]
