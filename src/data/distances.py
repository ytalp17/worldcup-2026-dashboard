from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["team", "distance_km"]


class DistanceRepository:
    """Loads precomputed team travel distances (km) keyed by team name."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> dict[str, float]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        distances: dict[str, float] = {}
        for _, row in df.iterrows():
            try:
                distances[str(row["team"])] = float(row["distance_km"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric distance in row: {row.to_dict()}") from exc
        return distances
