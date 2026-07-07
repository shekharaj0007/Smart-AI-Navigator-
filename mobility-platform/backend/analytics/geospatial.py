"""Geospatial analytics for GPS trajectories."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from config import STOP_MIN_SECONDS, STOP_SPEED_KMH

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def add_kinematics(df: pd.DataFrame) -> pd.DataFrame:
    """Add distance, speed, and acceleration columns to ordered GPS points."""
    if len(df) < 2:
        out = df.copy()
        out["distance_km"] = 0.0
        out["speed_kmh"] = 0.0
        out["acceleration_ms2"] = 0.0
        return out

    out = df.sort_values("timestamp").copy().reset_index(drop=True)
    lats = out["latitude"].values
    lons = out["longitude"].values
    times = out["timestamp"].values.astype("datetime64[ns]")

    distances = [0.0]
    speeds = [0.0]
    accels = [0.0]

    for i in range(1, len(out)):
        d = haversine_km(lats[i - 1], lons[i - 1], lats[i], lons[i])
        dt = (times[i] - times[i - 1]) / np.timedelta64(1, "s")
        speed = (d / dt * 3600) if dt > 0 else 0.0
        distances.append(d)
        speeds.append(speed)
        if i >= 2 and dt > 0:
            prev_dt = (times[i - 1] - times[i - 2]) / np.timedelta64(1, "s")
            if prev_dt > 0:
                prev_speed_ms = speeds[i - 1] / 3.6
                curr_speed_ms = speed / 3.6
                accels.append((curr_speed_ms - prev_speed_ms) / dt)
            else:
                accels.append(0.0)
        else:
            accels.append(0.0)

    out["distance_km"] = distances
    out["speed_kmh"] = speeds
    out["acceleration_ms2"] = accels
    return out


def trip_analytics(trip_points: pd.DataFrame) -> dict:
    """Compute analytics for a single trip."""
    if trip_points.empty:
        return {}

    kin = add_kinematics(trip_points)
    duration = (kin["timestamp"].max() - kin["timestamp"].min()).total_seconds()
    total_km = float(kin["distance_km"].sum())
    avg_speed = float(kin["speed_kmh"].mean())
    max_speed = float(kin["speed_kmh"].max())
    stops = detect_stops(kin)

    return {
        "point_count": len(kin),
        "duration_seconds": duration,
        "distance_km": round(total_km, 3),
        "avg_speed_kmh": round(avg_speed, 2),
        "max_speed_kmh": round(max_speed, 2),
        "stop_count": len(stops),
        "start_time": kin["timestamp"].min(),
        "end_time": kin["timestamp"].max(),
    }


def detect_stops(df: pd.DataFrame, speed_threshold: float = STOP_SPEED_KMH, min_seconds: int = STOP_MIN_SECONDS) -> list[dict]:
    """Detect stop events where speed stays below threshold."""
    if len(df) < 2:
        return []

    kin = add_kinematics(df) if "speed_kmh" not in df.columns else df
    stops: list[dict] = []
    start_idx = None

    for i, row in kin.iterrows():
        if row["speed_kmh"] < speed_threshold:
            if start_idx is None:
                start_idx = i
        elif start_idx is not None:
            start_row = kin.loc[start_idx]
            duration = (row["timestamp"] - start_row["timestamp"]).total_seconds()
            if duration >= min_seconds:
                stops.append(
                    {
                        "latitude": float(start_row["latitude"]),
                        "longitude": float(start_row["longitude"]),
                        "duration_seconds": duration,
                        "start_time": start_row["timestamp"],
                    }
                )
            start_idx = None

    return stops


def user_mobility_summary(points: pd.DataFrame, user_id: str) -> dict:
    """Aggregate mobility patterns for one user."""
    user_pts = points[points["user_id"] == user_id]
    if user_pts.empty:
        return {"user_id": user_id, "trips": 0}

    trips = user_pts.groupby("trip_id")
    trip_stats = []
    for trip_id, group in trips:
        stats = trip_analytics(group)
        stats["trip_id"] = trip_id
        trip_stats.append(stats)

    df = pd.DataFrame(trip_stats)
    hourly = user_pts.copy()
    hourly["hour"] = hourly["timestamp"].dt.hour
    peak_hour = int(hourly["hour"].mode().iloc[0]) if not hourly.empty else None

    return {
        "user_id": user_id,
        "trips": len(df),
        "total_distance_km": round(float(df["distance_km"].sum()), 2) if not df.empty else 0,
        "avg_trip_km": round(float(df["distance_km"].mean()), 2) if not df.empty else 0,
        "total_stops": int(df["stop_count"].sum()) if not df.empty else 0,
        "peak_hour": peak_hour,
    }


def hourly_traffic_pattern(points: pd.DataFrame) -> dict[int, int]:
    """Count GPS points per hour of day (proxy for activity)."""
    if points.empty:
        return {}
    hours = points.copy()
    hours["hour"] = hours["timestamp"].dt.hour
    counts = hours.groupby("hour").size()
    return {int(k): int(v) for k, v in counts.items()}


def heatmap_bins(points: pd.DataFrame, grid_size: float = 0.005) -> list[dict]:
    """Aggregate point density into lat/lon grid cells."""
    if points.empty:
        return []

    pts = points.copy()
    pts["lat_bin"] = (pts["latitude"] / grid_size).round() * grid_size
    pts["lon_bin"] = (pts["longitude"] / grid_size).round() * grid_size
    grouped = pts.groupby(["lat_bin", "lon_bin"]).size().reset_index(name="count")
    grouped = grouped.sort_values("count", ascending=False).head(500)

    return [
        {
            "latitude": float(r.lat_bin),
            "longitude": float(r.lon_bin),
            "count": int(r.count),
        }
        for r in grouped.itertuples()
    ]
