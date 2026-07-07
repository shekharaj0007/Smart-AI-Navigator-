"""Transportation mode classification from GPS segments."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.geospatial import add_kinematics, haversine_km
from config import MODELS_DIR, PROCESSED_DATA


FEATURE_COLUMNS = [
    "duration_min",
    "distance_km",
    "avg_speed_kmh",
    "max_speed_kmh",
    "speed_std",
    "stop_ratio",
    "point_density",
    "turn_rate",
    "avg_acceleration",
]


def extract_segment_features(segment: pd.DataFrame) -> dict | None:
    """Extract ML features from a labeled GPS segment."""
    if len(segment) < 3:
        return None

    kin = add_kinematics(segment)
    duration_s = (kin["timestamp"].max() - kin["timestamp"].min()).total_seconds()
    if duration_s <= 0:
        return None

    distance_km = float(kin["distance_km"].sum())
    speeds = kin["speed_kmh"].values
    stop_ratio = float((kin["speed_kmh"] < 1.0).mean())

    # Turn rate: bearing changes per minute
    bearings = []
    lats = kin["latitude"].values
    lons = kin["longitude"].values
    for i in range(1, len(kin)):
        b = _bearing(lats[i - 1], lons[i - 1], lats[i], lons[i])
        bearings.append(b)
    turn_rate = 0.0
    if len(bearings) > 1:
        turns = sum(abs(bearings[i] - bearings[i - 1]) for i in range(1, len(bearings)))
        turn_rate = turns / (duration_s / 60) if duration_s > 0 else 0

    return {
        "duration_min": duration_s / 60,
        "distance_km": distance_km,
        "avg_speed_kmh": float(np.mean(speeds)),
        "max_speed_kmh": float(np.max(speeds)),
        "speed_std": float(np.std(speeds)),
        "stop_ratio": stop_ratio,
        "point_density": len(kin) / (duration_s / 60) if duration_s > 0 else 0,
        "turn_rate": turn_rate,
        "avg_acceleration": float(np.mean(np.abs(kin["acceleration_ms2"].values))),
    }


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)
    dlon = np.radians(lon2 - lon1)
    x = np.sin(dlon) * np.cos(lat2_r)
    y = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)
    return float(np.degrees(np.arctan2(x, y)))


def build_training_data(points: pd.DataFrame) -> pd.DataFrame:
    """Build labeled feature dataset from GPS points with transport_mode."""
    labeled = points[points["transport_mode"].notna()].copy()
    if labeled.empty:
        return pd.DataFrame()

    rows = []
    for (user_id, mode), group in labeled.groupby(["user_id", "transport_mode"]):
        # Split continuous labeled runs by trip_id
        for trip_id, seg in group.groupby("trip_id"):
            feats = extract_segment_features(seg)
            if feats:
                feats["transport_mode"] = mode
                feats["user_id"] = user_id
                feats["trip_id"] = trip_id
                rows.append(feats)

    return pd.DataFrame(rows)


def train_classifier(points_path: Path | None = None) -> dict:
    """Train Random Forest transport mode classifier."""
    points_path = points_path or (PROCESSED_DATA / "gps_points.parquet")
    points = pd.read_parquet(points_path)
    data = build_training_data(points)

    if data.empty or data["transport_mode"].nunique() < 2:
        raise ValueError("Insufficient labeled data for training")

    X = data[FEATURE_COLUMNS]
    y = data["transport_mode"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=sorted(y.unique())).tolist()
    labels = sorted(y.unique())

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "transport_classifier.pkl"
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "labels": labels}, model_path)

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "samples": len(data),
        "classes": labels,
        "classification_report": report,
        "confusion_matrix": cm,
        "model_path": str(model_path),
    }

    metrics_path = MODELS_DIR / "training_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    print(f"Model saved to {model_path}")
    print(f"Accuracy: {accuracy:.2%}")
    print(classification_report(y_test, y_pred))

    return metrics


def predict_mode(segment: pd.DataFrame, model_path: Path | None = None) -> dict:
    """Predict transport mode for a GPS segment."""
    model_path = model_path or (MODELS_DIR / "transport_classifier.pkl")
    if not model_path.exists():
        raise FileNotFoundError("Model not trained. Run train_classifier() first.")

    bundle = joblib.load(model_path)
    model = bundle["model"]
    features = bundle["features"]

    feats = extract_segment_features(segment)
    if not feats:
        return {"error": "Segment too short for prediction"}

    X = pd.DataFrame([feats])[features]
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    classes = model.classes_

    return {
        "predicted_mode": pred,
        "confidence": round(float(max(proba)), 4),
        "probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
    }


if __name__ == "__main__":
    train_classifier()
