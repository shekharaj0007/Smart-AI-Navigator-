"""FastAPI application — AI Mobility Intelligence Platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assistant import answer_mobility_question
from app.data_store import get_store
from app.live_db import get_live_db
from app.live_service import record_ping
from app.live_simulator import is_simulating, start_simulation, stop_simulation
from app.ws_manager import ws_manager
from ml.transport_classifier import predict_mode

app = FastAPI(
    title="AI Mobility Intelligence Platform",
    description="Geolife GPS analytics, OD matrix, transport mode ML, and AI assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GPSPoint(BaseModel):
    latitude: float
    longitude: float
    timestamp: str
    altitude_m: float = 0.0


class PredictModeRequest(BaseModel):
    points: list[GPSPoint] = Field(..., min_length=3)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)


class CreateLiveTripRequest(BaseModel):
    rider_name: str = Field(..., min_length=1)
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    source_type: str = "real"


class LivePingRequest(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: float | None = None
    accuracy_m: float | None = None


class SimulateTripRequest(BaseModel):
    geolife_trip_id: str
    interval_sec: float = Field(default=2.0, ge=0.5, le=10.0)


@app.get("/api/health")
def health() -> dict:
    store = get_store()
    return {"status": "ok", "data_ready": store.ready}


@app.get("/api/stats")
def dataset_stats() -> dict:
    store = get_store()
    if not store.ready:
        raise HTTPException(503, "Run ETL first: python etl/run_etl.py")
    return store.stats


@app.get("/api/users")
def list_users() -> dict:
    store = get_store()
    if not store.ready:
        raise HTTPException(503, "Data not ready")
    return {"users": store.get_users(), "count": len(store.get_users())}


@app.get("/api/users/{user_id}/summary")
def user_summary(user_id: str) -> dict:
    store = get_store()
    return store.get_user_summary(user_id)


@app.get("/api/users/{user_id}/trajectories")
def user_trajectories(user_id: str, limit: int = 50) -> dict:
    store = get_store()
    trips = store.get_user_trips(user_id, limit=limit)
    return {"user_id": user_id, "trips": trips, "count": len(trips)}


@app.get("/api/trajectory/{trip_id}")
def trajectory_points(trip_id: str, max_points: int = 2000) -> dict:
    store = get_store()
    pts = store.get_trip_points(trip_id, max_points=max_points)
    if not pts:
        raise HTTPException(404, f"Trip {trip_id} not found")
    stats = store.get_trip_stats(trip_id)
    return {"trip_id": trip_id, "points": pts, "stats": stats}


@app.get("/api/heatmap")
def heatmap() -> dict:
    store = get_store()
    data = store.get_heatmap()
    return {"cells": data, "count": len(data)}


@app.get("/api/od-matrix")
def od_matrix(top_n: int = 50) -> dict:
    store = get_store()
    data = store.get_od_matrix(top_n=top_n)
    return {"flows": data, "count": len(data)}


@app.get("/api/traffic/hourly")
def hourly_traffic() -> dict:
    store = get_store()
    return {"hourly_counts": store.get_hourly_pattern()}


@app.get("/api/transport-modes")
def transport_modes() -> dict:
    store = get_store()
    modes = store.get_mode_distribution()
    total = sum(modes.values()) or 1
    return {
        "modes": modes,
        "percentages": {k: round(v / total * 100, 2) for k, v in modes.items()},
    }


@app.get("/api/ml/metrics")
def ml_metrics() -> dict:
    store = get_store()
    return store.get_training_metrics()


@app.post("/api/predict-mode")
def predict_transport_mode(req: PredictModeRequest) -> dict:
    df = pd.DataFrame([p.model_dump() for p in req.points])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    try:
        return predict_mode(df)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    store = get_store()
    if not store.ready:
        raise HTTPException(503, "Data not ready")
    return answer_mobility_question(req.question, store)


# --- Live Tracking (Blinkit-style) ---


@app.on_event("startup")
def init_live_db() -> None:
    get_live_db()


@app.post("/api/live/trips")
def create_live_trip(req: CreateLiveTripRequest) -> dict:
    db = get_live_db()
    trip = db.create_trip(
        rider_name=req.rider_name,
        origin_lat=req.origin_lat,
        origin_lon=req.origin_lon,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon,
        source_type=req.source_type,
    )
    return {"trip": trip}


@app.get("/api/live/trips")
def list_live_trips(status: str | None = None, limit: int = 50) -> dict:
    db = get_live_db()
    trips = db.list_trips(status=status, limit=limit)
    return {"trips": trips, "count": len(trips)}


@app.get("/api/live/trips/{trip_id}")
def get_live_trip(trip_id: str) -> dict:
    db = get_live_db()
    try:
        trip = db.get_trip(trip_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return {"trip": trip, "simulating": is_simulating(trip_id)}


@app.get("/api/live/trips/{trip_id}/share")
def get_share_info(trip_id: str) -> dict:
    db = get_live_db()
    try:
        trip = db.get_trip(trip_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return {
        "trip_id": trip_id,
        "rider_name": trip["rider_name"],
        "status": trip["status"],
        "share_path": f"/track/{trip_id}",
    }


@app.get("/api/live/trips/{trip_id}/history")
def get_live_trip_history(trip_id: str, limit: int = 5000) -> dict:
    db = get_live_db()
    try:
        db.get_trip(trip_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    history = db.get_ping_history(trip_id, limit=limit)
    return {"trip_id": trip_id, "pings": history, "count": len(history)}


@app.post("/api/live/trips/{trip_id}/ping")
async def post_live_ping(trip_id: str, req: LivePingRequest) -> dict:
    try:
        result = await record_ping(
            trip_id,
            req.latitude,
            req.longitude,
            req.speed_kmh,
            req.accuracy_m,
        )
        return result
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/live/trips/{trip_id}/complete")
def complete_live_trip(trip_id: str) -> dict:
    db = get_live_db()
    try:
        trip = db.complete_trip(trip_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    stop_simulation(trip_id)
    return {"trip": trip}


@app.post("/api/live/trips/{trip_id}/simulate")
async def simulate_live_trip(trip_id: str, req: SimulateTripRequest) -> dict:
    db = get_live_db()
    try:
        trip = db.get_trip(trip_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    store = get_store()
    if not store.ready:
        raise HTTPException(503, "Geolife data required for simulation")

    pts = store.get_trip_points(req.geolife_trip_id, max_points=5000)
    if len(pts) < 2:
        raise HTTPException(404, f"Geolife trip {req.geolife_trip_id} not found")

    first, last = pts[0], pts[-1]
    db.update_trip_route(
        trip_id,
        req.geolife_trip_id,
        first["latitude"],
        first["longitude"],
        last["latitude"],
        last["longitude"],
    )

    try:
        start_simulation(trip_id, req.geolife_trip_id, req.interval_sec)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e

    return {
        "message": "Simulation started",
        "trip_id": trip_id,
        "geolife_trip_id": req.geolife_trip_id,
        "points": len(pts),
        "interval_sec": req.interval_sec,
    }


@app.websocket("/ws/live/{trip_id}")
async def live_trip_websocket(websocket: WebSocket, trip_id: str) -> None:
    db = get_live_db()
    try:
        trip = db.get_trip(trip_id)
    except KeyError:
        await websocket.close(code=4004)
        return

    await ws_manager.connect(trip_id, websocket)
    await ws_manager.send_personal(
        websocket,
        {
            "type": "connected",
            "trip_id": trip_id,
            "trip": trip,
            "history": db.get_ping_history(trip_id, limit=500),
        },
    )

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await record_ping(
                    trip_id,
                    float(data["latitude"]),
                    float(data["longitude"]),
                    data.get("speed_kmh"),
                    data.get("accuracy_m"),
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(trip_id, websocket)
