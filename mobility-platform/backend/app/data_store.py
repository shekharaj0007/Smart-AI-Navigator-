"""Load and cache processed dataset."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.geospatial import heatmap_bins, hourly_traffic_pattern, trip_analytics, user_mobility_summary
from analytics.od_matrix import build_od_matrix, od_to_records
from config import MODELS_DIR, PROCESSED_DATA


class DataStore:
    def __init__(self) -> None:
        self.points_path = PROCESSED_DATA / "gps_points.parquet"
        self.trips_path = PROCESSED_DATA / "trips_summary.parquet"
        self.labels_path = PROCESSED_DATA / "transport_labels.parquet"
        self.stats_path = PROCESSED_DATA / "dataset_stats.json"
        self._points: pd.DataFrame | None = None
        self._trips: pd.DataFrame | None = None
        self._labels: pd.DataFrame | None = None
        self._stats: dict | None = None
        self._od_matrix: pd.DataFrame | None = None

    @property
    def ready(self) -> bool:
        return self.points_path.exists() and self.trips_path.exists()

    def load(self) -> None:
        if not self.ready:
            raise FileNotFoundError(
                "Processed data not found. Run: python etl/run_etl.py"
            )
        self._points = pd.read_parquet(self.points_path)
        self._trips = pd.read_parquet(self.trips_path)
        if self.labels_path.exists():
            self._labels = pd.read_parquet(self.labels_path)
        if self.stats_path.exists():
            self._stats = json.loads(self.stats_path.read_text(encoding="utf-8"))

    @property
    def points(self) -> pd.DataFrame:
        if self._points is None:
            self.load()
        return self._points  # type: ignore[return-value]

    @property
    def trips(self) -> pd.DataFrame:
        if self._trips is None:
            self.load()
        return self._trips  # type: ignore[return-value]

    @property
    def labels(self) -> pd.DataFrame:
        if self._labels is None:
            self.load()
        return self._labels if self._labels is not None else pd.DataFrame()

    @property
    def stats(self) -> dict:
        if self._stats is None:
            self.load()
        return self._stats or {}

    def get_users(self) -> list[str]:
        return sorted(self.points["user_id"].unique().tolist())

    def get_user_trips(self, user_id: str, limit: int = 50) -> list[dict]:
        trips = self.trips[self.trips["user_id"] == user_id].head(limit)
        return trips.to_dict(orient="records")

    def get_trip_points(self, trip_id: str, max_points: int = 2000) -> list[dict]:
        pts = self.points[self.points["trip_id"] == trip_id].sort_values("timestamp")
        if len(pts) > max_points:
            step = max(1, len(pts) // max_points)
            pts = pts.iloc[::step]
        records = pts[["latitude", "longitude", "altitude_m", "timestamp", "transport_mode"]].copy()
        records["timestamp"] = records["timestamp"].astype(str)
        return records.to_dict(orient="records")

    def get_heatmap(self) -> list[dict]:
        return heatmap_bins(self.points)

    def get_od_matrix(self, top_n: int = 50) -> list[dict]:
        if self._od_matrix is None:
            self._od_matrix = build_od_matrix(self.trips, top_n=top_n)
        return od_to_records(self._od_matrix.head(top_n))

    def get_hourly_pattern(self) -> dict:
        return hourly_traffic_pattern(self.points)

    def get_user_summary(self, user_id: str) -> dict:
        return user_mobility_summary(self.points, user_id)

    def get_trip_stats(self, trip_id: str) -> dict:
        pts = self.points[self.points["trip_id"] == trip_id]
        stats = trip_analytics(pts)
        stats["trip_id"] = trip_id
        return stats

    def get_mode_distribution(self) -> dict:
        if self.labels.empty:
            labeled = self.points[self.points["transport_mode"].notna()]
            if labeled.empty:
                return {}
            return labeled["transport_mode"].value_counts().to_dict()
        return self.labels["transport_mode"].value_counts().to_dict()

    def get_training_metrics(self) -> dict:
        path = MODELS_DIR / "training_metrics.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    store = DataStore()
    if store.ready:
        store.load()
    return store
