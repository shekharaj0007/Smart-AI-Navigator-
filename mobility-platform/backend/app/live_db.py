"""SQLite storage for live trip tracking."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import LIVE_DB_PATH


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveTrackingDB:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or LIVE_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS live_trips (
                    id TEXT PRIMARY KEY,
                    rider_name TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'real',
                    geolife_trip_id TEXT,
                    origin_lat REAL NOT NULL,
                    origin_lon REAL NOT NULL,
                    dest_lat REAL NOT NULL,
                    dest_lon REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    eta_minutes REAL,
                    remaining_km REAL,
                    started_at TEXT,
                    arrived_at TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS location_pings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_kmh REAL,
                    accuracy_m REAL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (trip_id) REFERENCES live_trips(id)
                );

                CREATE INDEX IF NOT EXISTS idx_pings_trip ON location_pings(trip_id);
                CREATE INDEX IF NOT EXISTS idx_pings_time ON location_pings(recorded_at);
                """
            )

    def create_trip(
        self,
        rider_name: str,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        source_type: str = "real",
        geolife_trip_id: str | None = None,
    ) -> dict[str, Any]:
        trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
        now = _utcnow()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO live_trips (
                    id, rider_name, source_type, geolife_trip_id,
                    origin_lat, origin_lon, dest_lat, dest_lon,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    trip_id,
                    rider_name,
                    source_type,
                    geolife_trip_id,
                    origin_lat,
                    origin_lon,
                    dest_lat,
                    dest_lon,
                    now,
                ),
            )
        return self.get_trip(trip_id)

    def get_trip(self, trip_id: str) -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM live_trips WHERE id = ?", (trip_id,)).fetchone()
            if not row:
                raise KeyError(f"Trip {trip_id} not found")
            trip = dict(row)
            latest = conn.execute(
                """
                SELECT * FROM location_pings
                WHERE trip_id = ?
                ORDER BY recorded_at DESC LIMIT 1
                """,
                (trip_id,),
            ).fetchone()
            trip["latest_ping"] = dict(latest) if latest else None
            trip["ping_count"] = conn.execute(
                "SELECT COUNT(*) FROM location_pings WHERE trip_id = ?", (trip_id,)
            ).fetchone()[0]
            return trip

    def list_trips(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM live_trips WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM live_trips ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def add_ping(
        self,
        trip_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: float | None = None,
        accuracy_m: float | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        ts = recorded_at or _utcnow()
        with self._conn() as conn:
            trip = conn.execute("SELECT status FROM live_trips WHERE id = ?", (trip_id,)).fetchone()
            if not trip:
                raise KeyError(f"Trip {trip_id} not found")
            if trip["status"] == "completed":
                raise ValueError("Trip already completed")

            if trip["status"] == "pending":
                conn.execute(
                    "UPDATE live_trips SET status = 'in_progress', started_at = ? WHERE id = ?",
                    (ts, trip_id),
                )

            cur = conn.execute(
                """
                INSERT INTO location_pings (trip_id, latitude, longitude, speed_kmh, accuracy_m, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (trip_id, latitude, longitude, speed_kmh, accuracy_m, ts),
            )
            ping_id = cur.lastrowid
            ping = conn.execute("SELECT * FROM location_pings WHERE id = ?", (ping_id,)).fetchone()
            return dict(ping)

    def update_eta(self, trip_id: str, eta_minutes: float, remaining_km: float) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE live_trips SET eta_minutes = ?, remaining_km = ? WHERE id = ?",
                (eta_minutes, remaining_km, trip_id),
            )

    def update_trip_route(
        self,
        trip_id: str,
        geolife_trip_id: str,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE live_trips SET
                    source_type = 'simulated',
                    geolife_trip_id = ?,
                    origin_lat = ?, origin_lon = ?,
                    dest_lat = ?, dest_lon = ?,
                    status = 'pending'
                WHERE id = ?
                """,
                (geolife_trip_id, origin_lat, origin_lon, dest_lat, dest_lon, trip_id),
            )

    def complete_trip(self, trip_id: str) -> dict[str, Any]:
        now = _utcnow()
        with self._conn() as conn:
            conn.execute(
                "UPDATE live_trips SET status = 'completed', arrived_at = ?, eta_minutes = 0, remaining_km = 0 WHERE id = ?",
                (now, trip_id),
            )
        return self.get_trip(trip_id)

    def get_ping_history(self, trip_id: str, limit: int = 5000) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM location_pings
                WHERE trip_id = ?
                ORDER BY recorded_at ASC
                LIMIT ?
                """,
                (trip_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_speeds(self, trip_id: str, n: int = 5) -> list[float]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT speed_kmh FROM location_pings
                WHERE trip_id = ? AND speed_kmh IS NOT NULL AND speed_kmh > 0
                ORDER BY recorded_at DESC LIMIT ?
                """,
                (trip_id, n),
            ).fetchall()
            return [float(r["speed_kmh"]) for r in rows]


_db: LiveTrackingDB | None = None


def get_live_db() -> LiveTrackingDB:
    global _db
    if _db is None:
        _db = LiveTrackingDB()
    return _db
