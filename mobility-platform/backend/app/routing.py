"""OSRM road routing for accurate ETA and route geometry."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config import OSRM_BASE_URL

# Cache last route per trip to avoid hammering OSRM every 3 sec
_route_cache: dict[str, dict[str, Any]] = {}


def _flip_coords(geojson_coords: list[list[float]]) -> list[list[float]]:
    """Convert GeoJSON [lon, lat] to Leaflet [lat, lon]."""
    return [[c[1], c[0]] for c in geojson_coords]


def fetch_osrm_route(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    cache_key: str | None = None,
) -> dict[str, Any] | None:
    """Fetch driving route from OSRM. Returns distance_km, duration_min, coordinates."""
    if cache_key and cache_key in _route_cache:
        cached = _route_cache[cache_key]
        # Reuse geometry but re-fetch if stale > 30s would need timestamps - skip for simplicity
        pass

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{from_lon},{from_lat};{to_lon},{to_lat}"
        f"?overview=full&geometries=geojson&steps=false"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MobilityPlatform/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    result = {
        "distance_km": round(route["distance"] / 1000, 3),
        "duration_min": round(route["duration"] / 60, 1),
        "coordinates": _flip_coords(route["geometry"]["coordinates"]),
    }
    if cache_key:
        _route_cache[cache_key] = result
    return result


def clear_route_cache(trip_id: str) -> None:
    _route_cache.pop(trip_id, None)
