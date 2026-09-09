"""
backend/db/event_store.py
-------------------------
Persistent SQLite event store for border surveillance incidents and forensic audit logs.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("EventStore")
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "events.db"


class EventStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        camera_id TEXT NOT NULL,
                        location TEXT NOT NULL,
                        category TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        description TEXT NOT NULL,
                        plate_number TEXT,
                        face_name TEXT,
                        track_id INTEGER,
                        snapshot_b64 TEXT,
                        metadata_json TEXT
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON security_events(priority)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON security_events(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_camera ON security_events(camera_id)")
                conn.commit()

    def log_event(
        self,
        category: str,
        priority: str,
        description: str,
        camera_id: str = "system",
        location: str = "Border Zone",
        plate_number: Optional[str] = None,
        face_name: Optional[str] = None,
        track_id: Optional[int] = None,
        snapshot_b64: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        event_id = str(uuid4())[:8].upper()
        ts_str = (timestamp or datetime.utcnow()).isoformat()
        meta_str = json.dumps(metadata or {})

        with self._lock:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO security_events (
                            event_id, timestamp, camera_id, location, category,
                            priority, description, plate_number, face_name,
                            track_id, snapshot_b64, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id, ts_str, camera_id, location, category,
                            priority, description, plate_number, face_name,
                            track_id, snapshot_b64, meta_str,
                        ),
                    )
                    conn.commit()
            except Exception as e:
                logger.error("[EventStore] Failed to log event: %s", e)

        return event_id

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        camera_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT event_id, timestamp, camera_id, location, category, priority, description, plate_number, face_name, track_id, (snapshot_b64 IS NOT NULL) AS has_snapshot, metadata_json FROM security_events WHERE 1=1"
        params = []

        if category and category != "ALL":
            query += " AND category = ?"
            params.append(category)
        if priority and priority != "ALL":
            query += " AND priority = ?"
            params.append(priority)
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        if search:
            query += " AND (description LIKE ? OR location LIKE ? OR plate_number LIKE ? OR face_name LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute(query, params).fetchall()
                results = []
                for r in rows:
                    meta = {}
                    try:
                        if r["metadata_json"]:
                            meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass
                    results.append(
                        {
                            "event_id": r["event_id"],
                            "timestamp": r["timestamp"],
                            "camera_id": r["camera_id"],
                            "location": r["location"],
                            "category": r["category"],
                            "priority": r["priority"],
                            "description": r["description"],
                            "plate_number": r["plate_number"],
                            "face_name": r["face_name"],
                            "track_id": r["track_id"],
                            "has_snapshot": bool(r["has_snapshot"]),
                            "metadata": meta,
                        }
                    )
                return results

    def get_event_count(self) -> int:
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute("SELECT COUNT(*) FROM security_events").fetchone()
                return row[0] if row else 0

    def get_snapshot(self, event_id: str) -> Optional[str]:
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT snapshot_b64 FROM security_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if row and row["snapshot_b64"]:
                    return row["snapshot_b64"]
        return None

    def export_csv(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> str:
        events = self.get_events(limit=5000, offset=0, category=category, priority=priority)
        output = io.StringIO()
        fieldnames = [
            "event_id", "timestamp", "camera_id", "location",
            "category", "priority", "description", "plate_number",
            "face_name", "track_id"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)
        return output.getvalue()

    def clear_events(self):
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM security_events")
                conn.commit()


# Global singleton instance
event_store = EventStore()
