"""ETA calculation for live tracking."""

from __future__ import annotations

import asyncio

from analytics.geospatial import haversine_km
from app.routing import fetch_osrm_route

DEFAULT_SPEED_KMH = 25.0
MIN_SPEED_KMH = 5.0
MAX_SPEED_KMH = 80.0


def compute_eta(
    current_lat: float,
    current_lon: float,
    dest_lat: float,
    dest_lon: float,
    recent_speeds_kmh: list[float] | None = None,
) -> dict[str, float | str | list | None]:
    """Estimate remaining time using haversine + recent GPS speed."""
    remaining_km = haversine_km(current_lat, current_lon, dest_lat, dest_lon)

    if remaining_km < 0.05:
        return {
            "remaining_km": 0.0,
            "eta_minutes": 0.0,
            "avg_speed_kmh": 0.0,
            "eta_source": "arrived",
            "route_geometry": None,
        }

    speeds = [s for s in (recent_speeds_kmh or []) if s and s > 0]
    if speeds:
        avg_speed = sum(speeds) / len(speeds)
        avg_speed = max(MIN_SPEED_KMH, min(MAX_SPEED_KMH, avg_speed))
    else:
        avg_speed = DEFAULT_SPEED_KMH

    eta_minutes = (remaining_km / avg_speed) * 60

    return {
        "remaining_km": round(remaining_km, 3),
        "eta_minutes": round(eta_minutes, 1),
        "avg_speed_kmh": round(avg_speed, 1),
        "eta_source": "gps",
        "route_geometry": None,
    }


async def compute_eta_with_routing(
    current_lat: float,
    current_lon: float,
    dest_lat: float,
    dest_lon: float,
    recent_speeds_kmh: list[float] | None = None,
    trip_id: str | None = None,
) -> dict[str, float | str | list | None]:
    """Blend GPS speed ETA with OSRM road routing when available."""
    basic = compute_eta(current_lat, current_lon, dest_lat, dest_lon, recent_speeds_kmh)

    if basic["remaining_km"] == 0:
        return basic

    osrm = await asyncio.to_thread(
        fetch_osrm_route,
        current_lat,
        current_lon,
        dest_lat,
        dest_lon,
        trip_id,
    )

    if not osrm:
        return basic

    gps_eta = float(basic["eta_minutes"])
    road_eta = float(osrm["duration_min"])
    road_km = float(osrm["distance_km"])

    # Blend road network time with recent rider speed
    if recent_speeds_kmh:
        blended = round(0.6 * road_eta + 0.4 * gps_eta, 1)
        source = "osrm+gps"
    else:
        blended = road_eta
        source = "osrm"

    return {
        "remaining_km": road_km,
        "eta_minutes": blended,
        "avg_speed_kmh": basic["avg_speed_kmh"],
        "eta_source": source,
        "route_geometry": osrm["coordinates"],
        "road_eta_minutes": road_eta,
        "gps_eta_minutes": gps_eta,
    }
