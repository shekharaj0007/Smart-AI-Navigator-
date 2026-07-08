# AI Mobility Intelligence Platform

End-to-end mobility analytics platform built on the **Microsoft Geolife GPS dataset**.
# 📸 Application Screenshots

![AI Mobility Assistant](ASSETS/AI%20Mobility%20Assistant.png)

![Live Tracker](ASSETS/LIVE%20TRACKER.png)

![Location Saving](ASSETS/Location%20saving%20in%20Database.png)

![Map Explorer](ASSETS/Map%20Explorer.png)

![Mobility Live Track](ASSETS/Mobility%20Live%20Track.png)

![Origin Destination Matrix](ASSETS/Origin%20Destination%20Matrix.png)

![Traffic Analytics](ASSETS/Traffic%20analytics.png)

## Features

| Phase | Module | Description |
|-------|--------|-------------|
| 1 | ETL Pipeline | Parse `.plt` files, clean GPS, segment trips, join labels |
| 2 | Geospatial Analytics | Distance, speed, stops, heatmaps, user summaries |
| 3 | OD Matrix | Grid-based origin–destination trip flows |
| 4 | ML Classifier | Random Forest transport mode prediction |
| 5 | FastAPI Backend | REST API for all analytics |
| 6 | React Dashboard | Maps, charts, OD table, traffic patterns |
| 7 | AI Assistant | Natural-language queries over mobility data |
| 8 | **Live Tracking** | Blinkit-style rider tracking, ETA, SQLite history |

## Quick Start

### 1. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run ETL (processes all Geolife trajectories)

```bash
python etl/run_etl.py
```

### 3. Train ML model

```bash
python run_training.py
```

### 4. Start API

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 5. Start frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Dataset

Raw data expected at:
```
../Geolife Trajectories 1.3/Data/
```

Processed output:
```
data/processed/
├── gps_points.parquet
├── trips_summary.parquet
├── transport_labels.parquet
├── od_matrix.parquet
└── dataset_stats.json
```

## API Endpoints

- `GET /api/stats` — Dataset overview
- `GET /api/users` — List users
- `GET /api/users/{id}/trajectories` — User trips
- `GET /api/trajectory/{trip_id}` — GPS points for map
- `GET /api/heatmap` — Density cells
- `GET /api/od-matrix` — OD flows
- `GET /api/traffic/hourly` — Hourly patterns
- `GET /api/transport-modes` — Mode distribution
- `POST /api/predict-mode` — ML prediction
- `POST /api/chat` — AI assistant

### Live tracking (Blinkit-style)

- `POST /api/live/trips` — Create delivery trip
- `POST /api/live/trips/{id}/ping` — Record GPS ping + ETA
- `GET /api/live/trips/{id}` — Trip status
- `GET /api/live/trips/{id}/history` — All stored timestamps
- `POST /api/live/trips/{id}/simulate` — Replay Geolife as live ride
- `WS /ws/live/{trip_id}` — Real-time location stream

**Option A (simulate):** Live Tracker → pick Geolife trip → Start simulated delivery  
**Option B (real GPS):** Rider App → Start trip → copy share link → open `/track/TRIP-XXX`

### Shareable tracking link

```
http://localhost:5173/track/TRIP-A1B2C3D4
```

Customer opens link directly — no login, live map + ETA + arrival notification.

### ETA sources

- **osrm** — road distance/time from OSRM routing
- **osrm+gps** — blended with rider's recent GPS speed
- **gps** — fallback haversine if OSRM unavailable

## Project Structure

```
mobility-platform/
├── backend/
│   ├── etl/           # Phase 1
│   ├── analytics/     # Phase 2 & 3
│   ├── ml/            # Phase 4
│   └── app/           # Phase 5 & 7
├── frontend/          # Phase 6
├── data/processed/
└── models/
```
