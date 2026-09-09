"""
backend/ingestion/ws_phone.py
------------------------------
WebSocket phone camera ingestor (Phase 7).

Receives frames from browser getUserMedia captured on the phone's browser.
The phone opens /phone_stream.html, which captures camera frames as JPEG
and sends them as base64-encoded strings over a WebSocket connection to
/ws/phone/{client_id}.

This module manages active phone stream queues.  The FastAPI ws_phone
endpoint populates the queues; the pipeline runner reads from them.

Phase: 7
"""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime
from typing import Dict, Optional

import cv2
import numpy as np

from backend.ingestion.frame_model import Frame
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# client_id → asyncio.Queue of Frame objects
_phone_queues: Dict[str, asyncio.Queue] = {}


def get_or_create_queue(client_id: str) -> asyncio.Queue:
    if client_id not in _phone_queues:
        _phone_queues[client_id] = asyncio.Queue(maxsize=30)
        logger.info("[WSPhone] Queue created for client '%s'", client_id)
    return _phone_queues[client_id]


def remove_queue(client_id: str) -> None:
    _phone_queues.pop(client_id, None)
    logger.info("[WSPhone] Queue removed for client '%s'", client_id)


async def push_frame_bytes(client_id: str, b64_jpeg: str, location: str = "Phone Camera") -> None:
    """
    Decode a base64 JPEG string and push it as a Frame into the client's queue.
    Called by the FastAPI WebSocket handler when a phone sends a frame.
    """
    try:
        raw = base64.b64decode(b64_jpeg)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("[WSPhone] Failed to decode frame from client '%s'", client_id)
            return

        target_w = settings.pipeline.frame_width
        target_h = settings.pipeline.frame_height
        if img.shape[1] != target_w or img.shape[0] != target_h:
            img = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        frame = Frame(
            camera_id=f"phone_{client_id}",
            location=location,
            timestamp=datetime.utcnow(),
            img=img,
        )
        q = get_or_create_queue(client_id)
        try:
            q.put_nowait(frame)
        except asyncio.QueueFull:
            logger.debug("[WSPhone] Queue full for client '%s' — dropping frame", client_id)
    except Exception as exc:
        logger.error("[WSPhone] Error processing frame from '%s': %s", client_id, exc)
