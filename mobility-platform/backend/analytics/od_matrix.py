"""Origin-Destination matrix from trip data."""

from __future__ import annotations

import pandas as pd

from config import OD_GRID_SIZE_DEG


def lat_lon_to_zone(lat: float, lon: float, grid_size: float = OD_GRID_SIZE_DEG) -> str:
    """Map coordinates to a grid zone identifier."""
    lat_cell = round(lat / grid_size) * grid_size
    lon_cell = round(lon / grid_size) * grid_size
    return f"{lat_cell:.3f}_{lon_cell:.3f}"


def zone_label(zone_id: str) -> str:
    """Human-readable zone label."""
    lat, lon = zone_id.split("_")
    return f"Z({lat},{lon})"


def build_od_matrix(trips: pd.DataFrame, grid_size: float = OD_GRID_SIZE_DEG, top_n: int = 100) -> pd.DataFrame:
    """Build origin-destination trip count matrix."""
    if trips.empty:
        return pd.DataFrame(columns=["origin", "destination", "origin_zone", "destination_zone", "trip_count"])

    df = trips.copy()
    df["origin_zone"] = df.apply(lambda r: lat_lon_to_zone(r["start_lat"], r["start_lon"], grid_size), axis=1)
    df["destination_zone"] = df.apply(lambda r: lat_lon_to_zone(r["end_lat"], r["end_lon"], grid_size), axis=1)

    # Skip same-zone micro trips
    df = df[df["origin_zone"] != df["destination_zone"]]

    od = (
        df.groupby(["origin_zone", "destination_zone"])
        .size()
        .reset_index(name="trip_count")
        .sort_values("trip_count", ascending=False)
        .head(top_n)
    )
    od["origin"] = od["origin_zone"].map(zone_label)
    od["destination"] = od["destination_zone"].map(zone_label)
    return od[["origin", "destination", "origin_zone", "destination_zone", "trip_count"]]


def od_to_records(od_df: pd.DataFrame) -> list[dict]:
    return od_df.to_dict(orient="records")
