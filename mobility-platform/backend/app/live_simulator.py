"""Replay Geolife trajectories as live GPS pings."""

from __future__ import annotations

import asyncio

from app.data_store import get_store
from app.live_db import get_live_db
from app.live_service import record_ping
from app.ws_manager import ws_manager

_active_simulations: dict[str, asyncio.Task] = {}


async def run_simulation(trip_id: str, geolife_trip_id: str, interval_sec: float = 2.0) -> None:
    """Stream Geolife points as timed live pings."""
    store = get_store()
    if not store.ready:
        raise RuntimeError("Geolife data not ready")

    db = get_live_db()
    points = store.get_trip_points(geolife_trip_id, max_points=5000)
    if len(points) < 2:
        raise ValueError(f"Geolife trip {geolife_trip_id} has insufficient points")

    try:
        prev = points[0]
        for i, pt in enumerate(points):
            if trip_id not in _active_simulations:
                break

            trip = db.get_trip(trip_id)
            if trip["status"] == "completed":
                break

            speed = None
            if i > 0:
                from analytics.geospatial import haversine_km

                dist = haversine_km(prev["latitude"], prev["longitude"], pt["latitude"], pt["longitude"])
                speed = min(80.0, max(0.0, (dist / interval_sec) * 3600))
            prev = pt

            result = await record_ping(trip_id, pt["latitude"], pt["longitude"], speed_kmh=speed)
            if result["trip"]["status"] == "completed":
                break

            await asyncio.sleep(interval_sec)

        trip = db.get_trip(trip_id)
        if trip["status"] != "completed":
            db.complete_trip(trip_id)
            await ws_manager.broadcast(
                trip_id,
                {
                    "type": "trip_completed",
                    "trip_id": trip_id,
                    "message": f"{trip['rider_name']} has arrived at the destination!",
                    "rider_name": trip["rider_name"],
                },
            )
    finally:
        _active_simulations.pop(trip_id, None)


def start_simulation(trip_id: str, geolife_trip_id: str, interval_sec: float = 2.0) -> None:
    if trip_id in _active_simulations:
        raise RuntimeError("Simulation already running for this trip")

    task = asyncio.create_task(run_simulation(trip_id, geolife_trip_id, interval_sec))
    _active_simulations[trip_id] = task


def stop_simulation(trip_id: str) -> None:
    _active_simulations.pop(trip_id, None)


def is_simulating(trip_id: str) -> bool:
    return trip_id in _active_simulations
