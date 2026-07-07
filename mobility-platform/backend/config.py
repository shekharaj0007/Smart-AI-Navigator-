from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent

# Raw Geolife dataset (sibling folder in archive)
GEOLIFE_DATA = PROJECT_ROOT.parent / "Geolife Trajectories 1.3" / "Data"

PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
LIVE_DB_PATH = PROJECT_ROOT / "data" / "live_tracking.db"

# ETL settings
TRIP_GAP_MINUTES = 30
FEET_TO_METERS = 0.3048
OD_GRID_SIZE_DEG = 0.01  # ~1.1 km at Beijing latitude

# Analytics thresholds
STOP_SPEED_KMH = 1.0
STOP_MIN_SECONDS = 60

# OSRM public routing server (road-aware ETA)
OSRM_BASE_URL = "https://router.project-osrm.org"
