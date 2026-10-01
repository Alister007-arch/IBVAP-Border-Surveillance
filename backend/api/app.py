"""
backend/api/app.py
--------------------
FastAPI application for IBVAP (Intelligent Border Video Analytics Platform).
REST endpoints + WebSocket frame/alert streaming + Dynamic Camera Management + Persistent Event Store.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

# Ensure project root is always in sys.path whether executed directly or as a package
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.config.network import get_lan_ip
from backend.engine import SurveillanceEngine
from backend.ingestion.frame_model import Frame
from backend.detection.night_switch import NightSwitcher
from backend.detection.tier3_motion import Tier3MotionDetector
from backend.detection.merger import merge_detections
from backend.tracking.tracker import WithinCameraTracker
from backend.alerts.section_coordinator import SectionCoordinator
from backend.alerts.schema import Alert
from backend.detection.visualizer import draw_detections, encode_jpeg
from backend.db.event_store import event_store


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for frame streaming and alerts.
    """

    def __init__(self):
        self.frame_subscribers: Dict[str, Set[WebSocket]] = {}
        self.alert_subscribers: Set[WebSocket] = set()

    async def connect_frames(self, ws: WebSocket, camera_id: str) -> None:
        await ws.accept()
        self.frame_subscribers.setdefault(camera_id, set()).add(ws)
        logger.info("[WS] Frame subscriber connected for camera '%s'", camera_id)

    async def connect_alerts(self, ws: WebSocket) -> None:
        await ws.accept()
        self.alert_subscribers.add(ws)
        logger.info("[WS] Alert subscriber connected")

    def disconnect_frames(self, ws: WebSocket, camera_id: str) -> None:
        subs = self.frame_subscribers.get(camera_id, set())
        subs.discard(ws)

    def disconnect_alerts(self, ws: WebSocket) -> None:
        self.alert_subscribers.discard(ws)

    async def broadcast_frame(self, camera_id: str, jpeg_bytes: bytes) -> None:
        """Send a JPEG frame as base64 to all subscribers for this camera."""
        subs = self.frame_subscribers.get(camera_id)
        if not subs:
            return

        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        msg = json.dumps({
            "type": "frame",
            "camera_id": camera_id,
            "data": b64,
        })
        dead: Set[WebSocket] = set()
        for ws in list(subs):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        for ws in dead:
            subs.discard(ws)

    async def broadcast_alert(self, alert_dict: dict) -> None:
        """Send an alert payload to all alert subscribers."""
        if alert_dict.get("priority") == "RED":
            try:
                from backend.alerts.sos_dispatcher import sos_dispatcher
                if sos_dispatcher.auto_dispatch_enabled:
                    sos_dispatcher.dispatch_alert(alert_dict)
            except Exception as e:
                logger.debug("[SOS] Dispatch call failed: %s", e)

        msg = json.dumps({"type": "alert", "payload": alert_dict})
        dead: Set[WebSocket] = set()
        for ws in list(self.alert_subscribers):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.alert_subscribers.discard(ws)


manager = ConnectionManager()
engine: Optional[SurveillanceEngine] = None
active_phone_cameras: Dict[str, dict] = {}
phone_sessions: Dict[str, dict] = {}

# ---------------------------------------------------------------------------
# App factory & lifespan
# ---------------------------------------------------------------------------

_lifespan_ref_count = 0
_cleanup_task: Optional[asyncio.Task] = None


async def cleanup_stale_phones():
    while True:
        try:
            await asyncio.sleep(6)
            now = time.time()
            stale = []
            for cid, s in list(phone_sessions.items()):
                if (now - s.get("last_seen", now)) > 25.0:
                    stale.append(cid)
            for cid in stale:
                s = phone_sessions.pop(cid, None)
                if s:
                    s["running"] = False
                    if s.get("worker_task"):
                        s["worker_task"].cancel()
                active_phone_cameras.pop(cid, None)
                await manager.broadcast_alert({
                    "alert_id": "SYS_CAM_UPDATE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "section": 1,
                    "section_title": "System Status",
                    "camera_id": cid,
                    "location": cid,
                    "category": "System",
                    "priority": "BLUE",
                    "description": f"Mobile patrol unit {cid} timed out.",
                    "group_size": 1,
                    "is_crossing": False,
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug("Cleanup stale phone error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, _lifespan_ref_count, _cleanup_task
    _lifespan_ref_count += 1

    if engine is None:
        logger.info("IBVAP Platform starting up (initializing singleton engine)...")
        engine = SurveillanceEngine(
            broadcast_frame_cb=manager.broadcast_frame,
            broadcast_alert_cb=manager.broadcast_alert,
        )
        await engine.start()
        _cleanup_task = asyncio.create_task(cleanup_stale_phones())
    else:
        logger.info("IBVAP Platform secondary server attached to existing engine instance.")

    yield

    _lifespan_ref_count -= 1
    if _lifespan_ref_count <= 0:
        if _cleanup_task:
            _cleanup_task.cancel()
        logger.info("IBVAP Platform shutting down...")
        if engine:
            await engine.stop()
            engine = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="IBVAP — Intelligent Border Video Analytics Platform",
        description="AI-based video analytics platform for border surveillance (SIH26187 / BSF / MHA)",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    phone_html_path = Path(__file__).parent.parent.parent / "frontend" / "public" / "phone_stream.html"

    # ------------------------------------------------------------------
    # REST endpoints: Core & Health
    # ------------------------------------------------------------------

    @app.get("/health")
    @app.get("/api/health")
    async def health():
        total_cams = (len(engine.workers) if engine else 0) + len(active_phone_cameras)
        return {
            "status": "ok",
            "platform": "IBVAP",
            "active_cameras": total_cams,
            "engine_running": engine is not None,
            "connected_phones": list(active_phone_cameras.keys()),
        }

    @app.get("/mobile-stream-info")
    @app.get("/api/mobile-stream-info")
    async def mobile_stream_info(request: Request):
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
        request_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        hostname = request_host.split(":")[0].lower()
        local_hosts = {"", "localhost", "127.0.0.1", "0.0.0.0"}

        lan_ip = get_lan_ip()
        tunnel_file = Path(__file__).resolve().parent.parent / "config" / "tunnel_url.txt"
        tunnel_url = ""
        if tunnel_file.exists():
            try:
                tunnel_url = tunnel_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        if tunnel_url and tunnel_url.startswith("http"):
            https_url = f"{tunnel_url}/phone_stream.html"
            direct_url = https_url
            host = tunnel_url.split("://")[-1]
            http_url = direct_url
        elif hostname in local_hosts:
            host = lan_ip
            https_url = f"https://{host}:8443/phone_stream.html"
            http_url = f"http://{host}:8000/phone_stream.html"
            direct_url = f"http://localhost:8000/phone_stream.html"
        else:
            host = request_host
            https_url = f"https://{host}/phone_stream.html"
            http_url = f"http://{host}/phone_stream.html"
            direct_url = f"{proto}://{host}/phone_stream.html"

        return {
            "host": host,
            "direct_url": direct_url,
            "https_url": https_url,
            "http_url": http_url,
            "tunnel_url": tunnel_url,
            "lan_url": f"http://{lan_ip}:8000/phone_stream.html",
            "lan_https_url": f"https://{lan_ip}:8443/phone_stream.html",
            "websocket_path": "/ws/phone/{client_id}",
            "post_path": "/api/phone/{client_id}/frame",
            "active_phones": list(active_phone_cameras.keys()),
        }

    # ------------------------------------------------------------------
    # REST endpoints: Camera Registry & Ingestion
    # ------------------------------------------------------------------

    @app.get("/cameras")
    @app.get("/api/cameras")
    async def list_cameras():
        registry_path = Path(__file__).parent.parent / "config" / "camera_registry.json"
        cameras = []
        try:
            if registry_path.exists():
                with open(registry_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        cameras = data.get("cameras", [])
        except Exception as e:
            logger.error("Error reading camera registry: %s", e)
            cameras = []

        # Merge live connected mobile units
        for phone_cam in active_phone_cameras.values():
            if not any(c["camera_id"] == phone_cam["camera_id"] for c in cameras):
                cameras.append(phone_cam)

        return {"cameras": cameras}

    @app.post("/api/cameras")
    async def add_camera_api(cam_data: dict):
        if not engine:
            raise HTTPException(status_code=500, detail="Surveillance engine not initialized")
        cid = cam_data.get("camera_id")
        if not cid:
            raise HTTPException(status_code=400, detail="camera_id is required")

        # Clean ID
        cam_data["camera_id"] = cid.strip().replace(" ", "_").lower()
        cam_data["enabled"] = True

        source_str = str(cam_data.get("source", "")).strip().lower()
        if "phone_stream.html" in source_str:
            raise HTTPException(
                status_code=400,
                detail=(
                    "phone_stream.html is the mobile streamer webpage, not an RTSP/MJPEG video feed. "
                    "To stream from a mobile phone, open the Mobile Streamer link directly on the phone "
                    "or click 'Open Streamer' in the top bar. The camera will connect automatically!"
                )
            )

        success = engine.add_camera(cam_data)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add camera")

        # Broadcast camera update to UI
        await manager.broadcast_alert({
            "alert_id": "SYS_CAM_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1,
            "section_title": "System Status",
            "camera_id": cam_data["camera_id"],
            "location": cam_data.get("location", cam_data["camera_id"]),
            "category": "System",
            "priority": "BLUE",
            "description": f"Camera node {cam_data['camera_id']} added and active.",
            "group_size": 1,
            "is_crossing": False,
        })

        return {"status": "ok", "camera_id": cam_data["camera_id"]}

    @app.delete("/api/cameras/{camera_id}")
    async def delete_camera_api(camera_id: str):
        if not engine:
            raise HTTPException(status_code=500, detail="Surveillance engine not initialized")

        # If it's a mobile phone camera
        if camera_id in active_phone_cameras:
            active_phone_cameras.pop(camera_id, None)
            return {"status": "ok", "removed": camera_id}

        removed = engine.remove_camera(camera_id)
        if not removed:
            raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

        await manager.broadcast_alert({
            "alert_id": "SYS_CAM_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1,
            "section_title": "System Status",
            "camera_id": camera_id,
            "location": camera_id,
            "category": "System",
            "priority": "BLUE",
            "description": f"Camera node {camera_id} removed.",
            "group_size": 1,
            "is_crossing": False,
        })

        return {"status": "ok", "removed": camera_id}

    # ------------------------------------------------------------------
    # REST endpoints: Persistent Event Store & Forensic Audit
    # ------------------------------------------------------------------

    @app.get("/api/events")
    async def get_events_api(
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        camera_id: Optional[str] = None,
        search: Optional[str] = None,
    ):
        events = event_store.get_events(
            limit=limit,
            offset=offset,
            category=category,
            priority=priority,
            camera_id=camera_id,
            search=search,
        )
        total = event_store.get_event_count()
        return {"events": events, "total": total}

    @app.get("/api/events/export")
    async def export_events_api(
        format: str = "csv",
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ):
        if format.lower() == "csv":
            csv_data = event_store.export_csv(category=category, priority=priority)
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=ibvap_incident_report.csv"},
            )
        else:
            events = event_store.get_events(limit=5000, category=category, priority=priority)
            return {"events": events}

    @app.get("/api/events/{event_id}/snapshot")
    async def get_snapshot_api(event_id: str):
        b64_snap = event_store.get_snapshot(event_id)
        if not b64_snap:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        img_bytes = base64.b64decode(b64_snap)
        return Response(content=img_bytes, media_type="image/jpeg")

    @app.delete("/api/events")
    async def clear_events_api():
        event_store.clear_events()
        return {"status": "ok", "message": "Audit event log cleared"}

    # ------------------------------------------------------------------
    # REST endpoints: System Control (Start / Stop / Reset)
    # ------------------------------------------------------------------

    @app.post("/api/system/stop")
    async def system_stop():
        """Pause all camera workers without removing them from the registry."""
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        for worker in engine.workers.values():
            worker.is_running = False
            if worker.task and not worker.task.done():
                worker.task.cancel()
        engine._is_running = False
        await manager.broadcast_alert({
            "alert_id": "SYS_CONTROL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1, "section_title": "System Status",
            "camera_id": "system", "location": "Command & Control",
            "category": "System", "priority": "AMBER",
            "description": "Surveillance engine STOPPED by operator.",
            "group_size": 1, "is_crossing": False,
        })
        return {"status": "stopped"}

    @app.post("/api/system/start")
    async def system_start():
        """Resume all camera workers from the registry."""
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        engine._is_running = True
        # Restart any cancelled workers
        for cid, worker in engine.workers.items():
            if not worker.is_running or (worker.task and worker.task.done()):
                worker.is_running = True
                worker.task = asyncio.create_task(worker.run_loop())
        await manager.broadcast_alert({
            "alert_id": "SYS_CONTROL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1, "section_title": "System Status",
            "camera_id": "system", "location": "Command & Control",
            "category": "System", "priority": "BLUE",
            "description": "Surveillance engine STARTED by operator.",
            "group_size": 1, "is_crossing": False,
        })
        return {"status": "running"}

    @app.post("/api/system/reset")
    async def system_reset():
        """Full reset: clear all event logs, remove all cameras, restart engine fresh."""
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        # Stop and remove all camera workers
        for worker in list(engine.workers.values()):
            worker.is_running = False
            if worker.task and not worker.task.done():
                worker.task.cancel()
        engine.workers.clear()
        active_phone_cameras.clear()
        # Clear persistent event store
        event_store.clear_events()
        # Wipe camera registry
        engine._is_running = True
        engine.save_registry()
        await manager.broadcast_alert({
            "alert_id": "SYS_RESET",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1, "section_title": "System Status",
            "camera_id": "system", "location": "Command & Control",
            "category": "System", "priority": "BLUE",
            "description": "Full system RESET performed. All cameras and audit logs cleared.",
            "group_size": 1, "is_crossing": False,
        })
        return {"status": "reset", "message": "System reset complete. Re-ingest cameras to restart surveillance."}

    # ------------------------------------------------------------------
    # REST endpoints: Watchlist Management & Face Photos (FRS & ANPR)
    # ------------------------------------------------------------------

    faces_dir = Path(__file__).resolve().parent.parent / "data" / "faces"
    faces_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/api/faces/{filename}")
    async def get_face_photo_api(filename: str):
        safe_name = Path(filename).name
        photo_path = faces_dir / safe_name
        if not photo_path.exists():
            raise HTTPException(status_code=404, detail="Face photo not found")
        with open(photo_path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type="image/jpeg")

    @app.post("/api/watchlist/upload_photo")
    async def upload_face_photo_api(payload: dict):
        person_id = payload.get("person_id", "SUSP")
        clean_pid = "".join(c for c in person_id if c.isalnum() or c in ("_", "-"))
        img_b64 = payload.get("image_data") or payload.get("image_base64", "")
        if not img_b64:
            raise HTTPException(status_code=400, detail="No image data provided")

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]

        try:
            img_bytes = base64.b64decode(img_b64)
            filename = f"{clean_pid}_{uuid4().hex[:8]}.jpg"
            save_path = faces_dir / filename
            with open(save_path, "wb") as f:
                f.write(img_bytes)

            photo_url = f"/api/faces/{filename}"
            return {"status": "ok", "url": photo_url, "filename": filename}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save photo: {e}")

    @app.get("/api/watchlist")
    async def get_watchlist_api():
        wl_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.json"
        if wl_path.exists():
            with open(wl_path, "r") as f:
                return json.load(f)
        return {"suspect_plates": [], "suspect_faces": []}

    @app.post("/api/watchlist")
    async def update_watchlist_api(payload: dict):
        wl_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.json"
        with open(wl_path, "w") as f:
            json.dump(payload, f, indent=2)

        # Dynamically reload facial gallery on surveillance coordinators and active phone sessions
        if engine and hasattr(engine, "reload_watchlist"):
            engine.reload_watchlist()

        for session in phone_sessions.values():
            coord = session.get("section_coordinator")
            if coord:
                if hasattr(coord, "face_detector"):
                    coord.face_detector.reload_gallery()
                if hasattr(coord, "anpr_detector"):
                    coord.anpr_detector._load_watchlist()

        return {"status": "ok"}

    # ------------------------------------------------------------------
    # WebSocket: frame streaming
    # ------------------------------------------------------------------

    @app.websocket("/ws/frames/{camera_id}")
    async def ws_frames(websocket: WebSocket, camera_id: str):
        await manager.connect_frames(websocket, camera_id)
        try:
            while True:
                await asyncio.sleep(30)
        except (WebSocketDisconnect, asyncio.CancelledError):
            manager.disconnect_frames(websocket, camera_id)
            logger.info("[WS] Frame subscriber disconnected for camera '%s'", camera_id)

    # ------------------------------------------------------------------
    # WebSocket: alert streaming
    # ------------------------------------------------------------------

    @app.websocket("/ws/alerts")
    async def ws_alerts(websocket: WebSocket):
        await manager.connect_alerts(websocket)
        try:
            while True:
                await asyncio.sleep(30)
        except (WebSocketDisconnect, asyncio.CancelledError):
            manager.disconnect_alerts(websocket)
            logger.info("[WS] Alert subscriber disconnected")

    # ------------------------------------------------------------------
    # Mobile Camera / Patrol Unit Ingestion with IBVAP AI Suite
    # (Supports Multiple Simultaneous Phones via HTTP POST or WebSocket)
    # ------------------------------------------------------------------

    @app.get("/api/phone/next-slot")
    async def get_next_phone_slot():
        """
        Dynamically finds the next unoccupied mobile phone slot (phone_1, phone_2, phone_3...)
        so multiple connected phones automatically get their own separate camera cards in the grid.
        """
        active_ids = set(active_phone_cameras.keys())
        for idx in range(1, 25):
            cand_id = f"phone_{idx}"
            if cand_id not in active_ids:
                return {
                    "client_id": cand_id,
                    "display_name": f"Phone {idx}",
                    "assigned_slot": idx,
                    "active_phones": list(active_ids),
                }
        uid = uuid4().hex[:4]
        return {
            "client_id": f"phone_{uid}",
            "display_name": f"Phone {uid}",
            "assigned_slot": len(active_ids) + 1,
            "active_phones": list(active_ids),
        }

    def get_or_create_phone_session(client_id: str, custom_name: Optional[str] = None):
        raw_id = (client_id or "").strip().replace(" ", "_").lower()
        if not raw_id or raw_id in ["phone_01", "phone", "undefined", "null"]:
            # Auto-assign next free slot if ambiguous or generic
            active_ids = set(active_phone_cameras.keys())
            found_slot = 1
            for idx in range(1, 25):
                if f"phone_{idx}" not in active_ids:
                    found_slot = idx
                    break
            raw_id = f"phone_{found_slot}"

        clean_id = raw_id if raw_id.startswith("phone_") else f"phone_{raw_id}"
        camera_id = clean_id

        display_name = custom_name.strip() if custom_name else raw_id.replace("phone_", "").replace("_", " ").title()
        location = f"Mobile Patrol ({display_name})"

        if camera_id in phone_sessions and phone_sessions[camera_id]["running"]:
            phone_sessions[camera_id]["last_seen"] = time.time()
            return phone_sessions[camera_id]

        phone_tracker = WithinCameraTracker(camera_id)
        night_switcher = NightSwitcher(camera_id)
        motion_detector = Tier3MotionDetector(camera_id)
        section_coordinator = SectionCoordinator(
            camera_id=camera_id,
            location=location,
            reid_matcher=engine.reid_matcher if engine else None,
        )

        frame_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=2)
        session: Dict[str, Any] = {
            "camera_id": camera_id,
            "client_id": client_id,
            "location": location,
            "display_name": display_name,
            "frame_queue": frame_queue,
            "running": True,
            "last_seen": time.time(),
            "worker_task": None,
            "phone_tracker": phone_tracker,
            "night_switcher": night_switcher,
            "motion_detector": motion_detector,
            "section_coordinator": section_coordinator,
        }

        active_phone_cameras[camera_id] = {
            "camera_id": camera_id,
            "location": location,
            "type": "ws_phone",
            "enabled": True,
        }

        def sync_process_frame(b64_str: str) -> Tuple[Optional[bytes], List[Alert]]:
            try:
                raw_bytes = base64.b64decode(b64_str)
                np_arr = np.frombuffer(raw_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is None:
                    return None, []

                h, w = img.shape[:2]
                if w > 640:
                    scale = 640.0 / w
                    img = cv2.resize(img, (640, int(h * scale)), interpolation=cv2.INTER_LINEAR)
                    h, w = img.shape[:2]

                boundary_line = ((0, int(h * 0.52)), (w, int(h * 0.52)))

                frame_obj = Frame(
                    camera_id=camera_id,
                    location=location,
                    timestamp=datetime.now(timezone.utc),
                    img=img,
                )

                proc_frame, is_night, _ = night_switcher.process(frame_obj)
                conf = settings.detection.night_confidence if is_night else settings.detection.day_confidence
                t1_dets = engine.detector_t1.detect(proc_frame, confidence=conf) if engine else []
                t2_dets = engine.detector_t2.detect(proc_frame, confidence=conf) if (engine and getattr(engine, "detector_t2", None)) else []
                t3_dets = motion_detector.detect(proc_frame)
                merged_dets = merge_detections(t1_dets, t2_dets, t3_dets)
                tracked_dets = phone_tracker.update(merged_dets, proc_frame.shape)
                alerts = section_coordinator.process(
                    proc_frame,
                    t1_dets,
                    t3_dets,
                    tracked_dets,
                    boundary_line=boundary_line,
                    is_night=is_night,
                )
                annotated = draw_detections(
                    proc_frame,
                    tracked_dets,
                    boundary_line=boundary_line,
                    crossing_ids=section_coordinator.virtual_fence._breached_tracks,
                    show_tier=False,
                    is_night=is_night,
                )
                jpeg_bytes = encode_jpeg(annotated, quality=60)
                return jpeg_bytes, alerts
            except Exception as e:
                logger.error("[Phone %s Error] %s", camera_id, e)
                return None, []

        async def worker_loop():
            while session["running"]:
                try:
                    b64_str = await frame_queue.get()
                    # Drain queue to guarantee zero-lag live frame delivery
                    while not frame_queue.empty():
                        try:
                            b64_str = frame_queue.get_nowait()
                        except Exception:
                            break
                    jpeg, alerts = await asyncio.to_thread(sync_process_frame, b64_str)
                    if jpeg:
                        await manager.broadcast_frame(camera_id, jpeg)
                    for alert in alerts:
                        await manager.broadcast_alert(alert.model_dump(mode="json"))
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("[Phone %s Loop Error] %s", camera_id, exc)

        session["worker_task"] = asyncio.create_task(worker_loop())
        phone_sessions[camera_id] = session

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast_alert({
                "alert_id": "SYS_CAM_UPDATE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "section": 1,
                "section_title": "System Status",
                "camera_id": camera_id,
                "location": location,
                "category": "System",
                "priority": "BLUE",
                "description": f"Mobile patrol unit '{display_name}' ({camera_id}) connected and active.",
                "group_size": 1,
                "is_crossing": False,
            }))
        except Exception:
            pass

        return session

    @app.post("/api/phone/{client_id}/frame")
    @app.post("/api/phone/frame")
    async def post_phone_frame(request: Request, client_id: str = "phone_01"):
        if request is None:
            raise HTTPException(status_code=400, detail="No request body provided")
        try:
            body = await request.json()
            b64_str = body.get("image") or body.get("data")
            custom_name = body.get("name")
            unit_id = body.get("client_id") or client_id
        except Exception:
            raw = await request.body()
            b64_str = raw.decode("utf-8")
            custom_name = None
            unit_id = client_id

        if not b64_str:
            raise HTTPException(status_code=400, detail="No frame data provided")

        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]

        session = get_or_create_phone_session(unit_id, custom_name)
        session["last_seen"] = time.time()
        q = session["frame_queue"]
        if q.full():
            try:
                q.get_nowait()
            except Exception:
                pass
        try:
            q.put_nowait(b64_str)
        except asyncio.QueueFull:
            pass

        return {"status": "ok", "camera_id": session["camera_id"]}

    @app.post("/api/phone/{client_id}/stop")
    async def stop_phone_stream(client_id: str):
        raw_id = client_id.strip().replace(" ", "_").lower()
        camera_id = raw_id if raw_id.startswith("phone_") else f"phone_{raw_id}"
        session = phone_sessions.pop(camera_id, None)
        if session:
            session["running"] = False
            if session.get("worker_task"):
                session["worker_task"].cancel()
        active_phone_cameras.pop(camera_id, None)
        await manager.broadcast_alert({
            "alert_id": "SYS_CAM_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1,
            "section_title": "System Status",
            "camera_id": camera_id,
            "location": camera_id,
            "category": "System",
            "priority": "BLUE",
            "description": f"Mobile patrol unit {camera_id} stopped.",
            "group_size": 1,
            "is_crossing": False,
        })
        return {"status": "ok", "stopped": camera_id}

    @app.websocket("/ws/phone/{client_id}")
    async def ws_phone(websocket: WebSocket, client_id: str):
        await websocket.accept()
        session = get_or_create_phone_session(client_id)
        camera_id = session["camera_id"]
        frame_queue = session["frame_queue"]
        logger.info("[Phone WS] Mobile patrol camera connected: %s", camera_id)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "__ping__":
                    session["last_seen"] = time.time()
                    continue
                session["last_seen"] = time.time()
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except Exception:
                        pass
                try:
                    frame_queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass

        except (WebSocketDisconnect, asyncio.CancelledError):
            logger.info("[Phone WS] Mobile camera disconnected: %s", camera_id)
        finally:
            session["last_seen"] = time.time()

    # ------------------------------------------------------------------
    # Acoustic Threat & Audio Intelligence Endpoints
    # ------------------------------------------------------------------

    @app.post("/api/audio/simulate-threat")
    async def simulate_audio_threat(req: Request):
        try:
            body = await req.json()
        except Exception:
            body = {}
        threat_type = body.get("threat_type", "GUNSHOT")
        from backend.detection.audio_detector import acoustic_detector
        threat = acoustic_detector.generate_simulated_threat(threat_type=threat_type)

        alert_dict = {
            "alert_id": str(uuid4())[:8],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "section": 1,
            "section_title": "Acoustic Threat Intelligence",
            "camera_id": threat["camera_id"],
            "location": threat["location"],
            "category": "Acoustic Threat",
            "priority": threat["priority"],
            "description": threat["description"],
            "predictive_heading": threat["bearing_azimuth"],
            "predictive_eta_sec": 12,
            "intercept_sector": "Sound Triangulation Sector Alpha",
            "bboxes": [],
        }
        await manager.broadcast_alert(alert_dict)

        event_store.log_event(
            category="Acoustic Threat",
            priority=threat["priority"],
            description=threat["description"],
            camera_id=threat["camera_id"],
            location=threat["location"],
        )
        return {"status": "ok", "threat": threat, "alert": alert_dict}

    # ------------------------------------------------------------------
    # SOS Emergency & Telegram QRF Dispatch Endpoints
    # ------------------------------------------------------------------

    @app.get("/api/sos/config")
    async def get_sos_config():
        from backend.alerts.sos_dispatcher import sos_dispatcher
        return sos_dispatcher.get_config()

    @app.post("/api/sos/config")
    async def set_sos_config(req: Request):
        body = await req.json()
        from backend.alerts.sos_dispatcher import sos_dispatcher
        sos_dispatcher.update_config(
            bot_token=body.get("bot_token"),
            chat_id=body.get("chat_id"),
            webhook_url=body.get("webhook_url"),
            auto_enabled=body.get("auto_enabled"),
        )
        return sos_dispatcher.get_config()

    @app.get("/api/sos/dispatches")
    async def get_sos_dispatches():
        from backend.alerts.sos_dispatcher import sos_dispatcher
        return {"dispatches": sos_dispatcher.recent_dispatches}

    @app.post("/api/sos/trigger-qrf")
    async def manual_trigger_qrf(req: Request):
        try:
            body = await req.json()
        except Exception:
            body = {}
        from backend.alerts.sos_dispatcher import sos_dispatcher
        record = sos_dispatcher.dispatch_alert({
            "description": body.get("description", "TACTICAL OPERATOR QRF DISPATCH: Immediate Intercept Ordered"),
            "location": body.get("location", "Sector-4 Buffer Line"),
            "category": "Manual QRF Command",
            "predictive_eta_sec": body.get("eta", 28),
            "predictive_heading": body.get("heading", "315° NW"),
            "intercept_sector": body.get("sector", "Sector-4 Buffer Line"),
        })
        return {"status": "dispatched", "record": record}

    # ------------------------------------------------------------------
    # Serve phone capture HTML page
    # ------------------------------------------------------------------

    @app.get("/phone_stream.html", response_class=HTMLResponse)
    async def phone_stream_page():
        if phone_html_path.exists():
            return HTMLResponse(phone_html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>phone_stream.html not found</h1>")

    # ------------------------------------------------------------------
    # Serve React Dashboard (dist)
    # ------------------------------------------------------------------

    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/")
        async def serve_root():
            return FileResponse(frontend_dist / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("ws/") or full_path in ("api", "ws"):
                raise HTTPException(status_code=404, detail="Endpoint not found")
            target = frontend_dist / full_path
            if target.is_file():
                return FileResponse(target)
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"status": "ok"}
    else:
        @app.get("/")
        async def root():
            return {
                "service": "IBVAP — Intelligent Border Video Analytics Platform",
                "version": "1.0.0",
                "status": "online",
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.app:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(_PROJECT_ROOT))
