"""Shared logic for recording a live GPS ping."""

from __future__ import annotations

from app.eta import compute_eta_with_routing
from app.live_db import get_live_db
from app.ws_manager import ws_manager


async def record_ping(
    trip_id: str,
    latitude: float,
    longitude: float,
    speed_kmh: float | None = None,
    accuracy_m: float | None = None,
    broadcast: bool = True,
) -> dict:
    db = get_live_db()
    trip = db.get_trip(trip_id)
    ping = db.add_ping(trip_id, latitude, longitude, speed_kmh, accuracy_m)
    speeds = db.get_recent_speeds(trip_id)
    eta = await compute_eta_with_routing(
        latitude,
        longitude,
        trip["dest_lat"],
        trip["dest_lon"],
        speeds,
        trip_id=trip_id,
    )
    db.update_eta(trip_id, float(eta["eta_minutes"]), float(eta["remaining_km"]))

    remaining_km = float(eta["remaining_km"])
    if remaining_km < 0.05:
        db.complete_trip(trip_id)
        payload = {
            "type": "trip_completed",
            "trip_id": trip_id,
            "ping": ping,
            "eta_minutes": 0,
            "remaining_km": 0,
            "message": f"{trip['rider_name']} has arrived at the destination!",
            "rider_name": trip["rider_name"],
        }
    else:
        payload = {
            "type": "location_update",
            "trip_id": trip_id,
            "ping": ping,
            "eta_minutes": eta["eta_minutes"],
            "remaining_km": eta["remaining_km"],
            "avg_speed_kmh": eta["avg_speed_kmh"],
            "eta_source": eta.get("eta_source"),
            "route_geometry": eta.get("route_geometry"),
            "status": "in_progress",
        }

    if broadcast:
        await ws_manager.broadcast(trip_id, payload)

    updated = db.get_trip(trip_id)
    return {
        "trip": updated,
        "ping": ping,
        "eta_minutes": eta["eta_minutes"],
        "remaining_km": eta["remaining_km"],
        "avg_speed_kmh": eta["avg_speed_kmh"],
        "eta_source": eta.get("eta_source"),
        "route_geometry": eta.get("route_geometry"),
    }
