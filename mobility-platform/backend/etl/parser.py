"""Parse Geolife .plt trajectory files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from config import FEET_TO_METERS


def parse_plt(path: Path, user_id: str) -> pd.DataFrame:
    """Parse a single .plt file into a DataFrame of GPS points."""
    rows: list[dict] = []
    trajectory_id = path.stem

    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Data starts after line 6 (0-indexed: skip header lines 0-5)
    for line in lines[6:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            lat = float(parts[0])
            lon = float(parts[1])
            alt_ft = float(parts[3]) if parts[3] else 0.0
            date_str = parts[5].strip()
            time_str = parts[6].strip()
            ts = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError):
            continue

        rows.append(
            {
                "user_id": user_id,
                "trajectory_id": trajectory_id,
                "latitude": lat,
                "longitude": lon,
                "altitude_m": alt_ft * FEET_TO_METERS,
                "timestamp": ts,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "user_id",
                "trajectory_id",
                "latitude",
                "longitude",
                "altitude_m",
                "timestamp",
            ]
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def discover_plt_files(data_root: Path) -> list[tuple[str, Path]]:
    """Return (user_id, plt_path) for all trajectory files."""
    files: list[tuple[str, Path]] = []
    if not data_root.exists():
        return files

    for user_dir in sorted(data_root.iterdir()):
        if not user_dir.is_dir():
            continue
        traj_dir = user_dir / "Trajectory"
        if not traj_dir.exists():
            continue
        user_id = user_dir.name
        for plt in sorted(traj_dir.glob("*.plt")):
            files.append((user_id, plt))
    return files
