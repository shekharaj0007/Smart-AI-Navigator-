"""LLM-style analytics assistant grounded in Geolife data."""

from __future__ import annotations

import re
from typing import Any

from app.data_store import DataStore


def answer_mobility_question(question: str, store: DataStore) -> dict[str, Any]:
    """Rule-based NL analytics — answers from precomputed stats, no external LLM required."""
    q = question.lower().strip()
    stats = store.stats
    response: dict[str, Any] = {"question": question, "sources": ["geolife_processed_data"]}

    if not stats:
        response["answer"] = "Dataset not processed yet. Run the ETL pipeline first."
        return response

    if any(w in q for w in ["overview", "summary", "about", "dataset", "how many"]):
        response["answer"] = (
            f"The Geolife dataset in this platform contains {stats.get('users', 0)} users, "
            f"{stats.get('trips', 0):,} trips, and {stats.get('gps_points', 0):,} GPS points. "
            f"{stats.get('labeled_users', 0)} users have transport mode labels across "
            f"{stats.get('labeled_segments', 0):,} annotated segments."
        )
        response["data"] = stats
        return response

    if any(w in q for w in ["transport", "mode", "common", "bus", "walk", "car", "train"]):
        modes = store.get_mode_distribution()
        if not modes:
            response["answer"] = "No transport mode labels available."
            return response
        top = max(modes, key=modes.get)  # type: ignore[arg-type]
        total = sum(modes.values())
        pct = modes[top] / total * 100
        breakdown = ", ".join(f"{k}: {v} ({v/total*100:.1f}%)" for k, v in sorted(modes.items(), key=lambda x: -x[1]))
        response["answer"] = f"The most common transport mode is **{top}** ({pct:.1f}%). Breakdown: {breakdown}."
        response["chart"] = {"type": "bar", "data": modes}
        return response

    if any(w in q for w in ["traffic", "peak", "rush", "hour", "busy"]):
        hourly = store.get_hourly_pattern()
        if not hourly:
            response["answer"] = "No hourly pattern data available."
            return response
        peak = max(hourly, key=hourly.get)  # type: ignore[arg-type]
        response["answer"] = (
            f"Peak mobility activity occurs around **{peak}:00–{peak+1}:00** "
            f"with {hourly[peak]:,} GPS samples. "
            f"Morning rush (7–10 AM): {sum(hourly.get(h, 0) for h in range(7, 11)):,} points. "
            f"Evening rush (17–20): {sum(hourly.get(h, 0) for h in range(17, 21)):,} points."
        )
        response["chart"] = {"type": "line", "data": hourly}
        return response

    if any(w in q for w in ["od", "origin", "destination", "flow", "zone", "route"]):
        od = store.get_od_matrix(top_n=5)
        if not od:
            response["answer"] = "No OD flows computed."
            return response
        lines = [f"{r['origin']} → {r['destination']}: {r['trip_count']} trips" for r in od[:5]]
        response["answer"] = "Top origin–destination flows:\n" + "\n".join(lines)
        response["chart"] = {"type": "od_table", "data": od}
        return response

    if any(w in q for w in ["heatmap", "hotspot", "density", "popular", "location"]):
        heat = store.get_heatmap()[:5]
        if not heat:
            response["answer"] = "No heatmap data."
            return response
        lines = [f"({h['latitude']:.4f}, {h['longitude']:.4f}): {h['count']:,} points" for h in heat]
        response["answer"] = "Highest-density locations:\n" + "\n".join(lines)
        response["chart"] = {"type": "heatmap", "data": heat}
        return response

    if any(w in q for w in ["accuracy", "model", "classifier", "predict", "ml"]):
        metrics = store.get_training_metrics()
        if not metrics:
            response["answer"] = "Transport mode classifier not trained yet."
            return response
        response["answer"] = (
            f"The transport mode classifier achieved **{metrics.get('accuracy', 0)*100:.1f}%** accuracy "
            f"on {metrics.get('samples', 0)} labeled segments. "
            f"Classes: {', '.join(metrics.get('classes', []))}."
        )
        response["data"] = metrics
        return response

    # User-specific query
    user_match = re.search(r"user\s*(\d+)", q)
    if user_match:
        user_id = user_match.group(1).zfill(3) if len(user_match.group(1)) < 3 else user_match.group(1)
        summary = store.get_user_summary(user_id)
        if summary.get("trips", 0) == 0:
            response["answer"] = f"No data found for user {user_id}."
        else:
            response["answer"] = (
                f"User {user_id}: {summary['trips']} trips, "
                f"{summary['total_distance_km']} km total, "
                f"avg {summary['avg_trip_km']} km/trip, "
                f"peak activity hour: {summary.get('peak_hour')}."
            )
            response["data"] = summary
        return response

    response["answer"] = (
        "I can answer questions about: dataset overview, transport modes, peak hours/traffic, "
        "OD flows, heatmap hotspots, ML model accuracy, or specific users (e.g. 'user 010 stats'). "
        "Try: 'Which transport mode is most common?' or 'Show peak traffic hours'."
    )
    return response
