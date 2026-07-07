"""Segment GPS points into trips."""

from __future__ import annotations

import pandas as pd

from config import TRIP_GAP_MINUTES


def segment_trips(df: pd.DataFrame, gap_minutes: int = TRIP_GAP_MINUTES) -> pd.DataFrame:
    """Assign trip_id within each user/trajectory based on time gaps."""
    if df.empty:
        return df

    out = df.copy().sort_values("timestamp").reset_index(drop=True)
    gap = pd.Timedelta(minutes=gap_minutes)

    time_diff = out["timestamp"].diff()
    new_trip = (time_diff > gap) | time_diff.isna()
    out["segment_num"] = new_trip.cumsum().astype(int)

    out["trip_id"] = (
        out["user_id"]
        + "_"
        + out["trajectory_id"].astype(str)
        + "_"
        + out["segment_num"].astype(str)
    )
    return out
