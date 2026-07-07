"""Parse Geolife transportation mode labels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse_labels(user_dir: Path, user_id: str) -> pd.DataFrame:
    """Parse labels.txt for a user if present."""
    label_path = user_dir / "labels.txt"
    if not label_path.exists():
        return pd.DataFrame(columns=["user_id", "start_time", "end_time", "transport_mode"])

    df = pd.read_csv(label_path, sep="\t", encoding="utf-8")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    df["user_id"] = user_id
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")
    df["transport_mode"] = df["transportation_mode"].str.strip().str.lower()

    return df[["user_id", "start_time", "end_time", "transport_mode"]].dropna(
        subset=["start_time", "end_time"]
    )


def assign_transport_modes(points: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Join transport mode labels to GPS points by timestamp overlap."""
    if points.empty or labels.empty:
        out = points.copy()
        out["transport_mode"] = None
        return out

    out = points.copy()
    out["transport_mode"] = None

    for _, label in labels.iterrows():
        mask = (out["timestamp"] >= label["start_time"]) & (out["timestamp"] <= label["end_time"])
        out.loc[mask, "transport_mode"] = label["transport_mode"]

    return out
