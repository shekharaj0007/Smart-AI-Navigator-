"""Train transport classifier and export OD matrix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analytics.od_matrix import build_od_matrix
from config import PROCESSED_DATA
from ml.transport_classifier import train_classifier


def main() -> None:
    print("Training transport mode classifier...")
    metrics = train_classifier()
    print(f"Accuracy: {metrics['accuracy']}")

    trips = __import__("pandas").read_parquet(PROCESSED_DATA / "trips_summary.parquet")
    od = build_od_matrix(trips, top_n=100)
    od_path = PROCESSED_DATA / "od_matrix.parquet"
    od.to_parquet(od_path, index=False)
    print(f"OD matrix saved: {od_path} ({len(od)} flows)")


if __name__ == "__main__":
    main()
