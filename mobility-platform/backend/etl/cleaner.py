"""Clean and validate GPS trajectory points."""

from __future__ import annotations

import pandas as pd

# Beijing approximate bounds (+ margin for nearby travel)
BEIJING_LAT_MIN, BEIJING_LAT_MAX = 39.4, 41.1
BEIJING_LON_MIN, BEIJING_LON_MAX = 115.4, 117.5


def clean_points(df: pd.DataFrame) -> pd.DataFrame:
    """Remove invalid, out-of-bounds, and duplicate GPS points."""
    if df.empty:
        return df

    out = df.copy()
    out = out.dropna(subset=["latitude", "longitude", "timestamp"])

    # Remove null island and obvious bad coords
    out = out[(out["latitude"] != 0) | (out["longitude"] != 0)]
    out = out[out["latitude"].between(-90, 90)]
    out = out[out["longitude"].between(-180, 180)]

    # Keep points in/near Beijing (dataset coverage)
    out = out[
        out["latitude"].between(BEIJING_LAT_MIN, BEIJING_LAT_MAX)
        & out["longitude"].between(BEIJING_LON_MIN, BEIJING_LON_MAX)
    ]

    out = out.sort_values("timestamp")
    out = out.drop_duplicates(subset=["latitude", "longitude", "timestamp"], keep="first")
    return out.reset_index(drop=True)
