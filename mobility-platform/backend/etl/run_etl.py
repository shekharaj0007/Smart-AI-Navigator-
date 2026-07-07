"""Run full ETL pipeline on Geolife dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import GEOLIFE_DATA, PROCESSED_DATA
from etl.cleaner import clean_points
from etl.labels import assign_transport_modes, parse_labels
from etl.parser import discover_plt_files, parse_plt
from etl.segmenter import segment_trips


def run_etl(data_root: Path | None = None, batch_size: int = 200) -> dict:
    data_root = data_root or GEOLIFE_DATA
    PROCESSED_DATA.mkdir(parents=True, exist_ok=True)

    plt_files = discover_plt_files(data_root)
    if not plt_files:
        raise FileNotFoundError(f"No .plt files found under {data_root}")

    all_labels: list[pd.DataFrame] = []
    point_batches: list[pd.DataFrame] = []
    batch: list[pd.DataFrame] = []
    labels_cache: dict[str, pd.DataFrame] = {}

    print(f"Processing {len(plt_files)} trajectory files from {data_root}...", flush=True)

    for i, (user_id, plt_path) in enumerate(plt_files, 1):
        if user_id not in labels_cache:
            labels_cache[user_id] = parse_labels(data_root / user_id, user_id)
            if not labels_cache[user_id].empty:
                all_labels.append(labels_cache[user_id])

        labels = labels_cache[user_id]

        df = parse_plt(plt_path, user_id)
        if df.empty:
            continue

        df = clean_points(df)
        if df.empty:
            continue

        df = segment_trips(df)
        if not labels.empty:
            df = assign_transport_modes(df, labels)

        batch.append(df)

        if len(batch) >= batch_size:
            point_batches.append(pd.concat(batch, ignore_index=True))
            batch = []
            print(f"  Processed {i}/{len(plt_files)} files...", flush=True)

    if batch:
        point_batches.append(pd.concat(batch, ignore_index=True))

    points = pd.concat(point_batches, ignore_index=True) if point_batches else pd.DataFrame()
    labels_df = pd.concat(all_labels, ignore_index=True).drop_duplicates() if all_labels else pd.DataFrame()

    points_path = PROCESSED_DATA / "gps_points.parquet"
    labels_path = PROCESSED_DATA / "transport_labels.parquet"
    trips_path = PROCESSED_DATA / "trips_summary.parquet"

    points.to_parquet(points_path, index=False)
    labels_df.to_parquet(labels_path, index=False)

    trips = build_trips_summary(points)
    trips.to_parquet(trips_path, index=False)

    stats = compute_stats(points, labels_df, trips, len(plt_files))
    stats_path = PROCESSED_DATA / "dataset_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")

    print("\n=== ETL Complete ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\nOutput: {PROCESSED_DATA}")

    return stats


def build_trips_summary(points: pd.DataFrame) -> pd.DataFrame:
    if points.empty:
        return pd.DataFrame()

    grouped = points.groupby("trip_id", as_index=False).agg(
        user_id=("user_id", "first"),
        trajectory_id=("trajectory_id", "first"),
        start_time=("timestamp", "min"),
        end_time=("timestamp", "max"),
        point_count=("timestamp", "count"),
        start_lat=("latitude", "first"),
        start_lon=("longitude", "first"),
        end_lat=("latitude", "last"),
        end_lon=("longitude", "last"),
        transport_mode=("transport_mode", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
    )
    grouped["duration_seconds"] = (
        grouped["end_time"] - grouped["start_time"]
    ).dt.total_seconds()
    return grouped


def compute_stats(
    points: pd.DataFrame,
    labels: pd.DataFrame,
    trips: pd.DataFrame,
    trajectory_files: int,
) -> dict:
    labeled_points = int(points["transport_mode"].notna().sum()) if not points.empty else 0
    return {
        "trajectory_files": trajectory_files,
        "users": int(points["user_id"].nunique()) if not points.empty else 0,
        "trips": int(len(trips)),
        "gps_points": int(len(points)),
        "labeled_users": int(labels["user_id"].nunique()) if not labels.empty else 0,
        "labeled_segments": int(len(labels)),
        "labeled_gps_points": labeled_points,
        "transport_modes": (
            labels["transport_mode"].value_counts().to_dict() if not labels.empty else {}
        ),
    }


if __name__ == "__main__":
    run_etl()
