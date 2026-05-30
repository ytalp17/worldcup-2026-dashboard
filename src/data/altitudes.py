from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["city", "altitude_m"]


class AltitudeRepository:
    """Loads stadium altitudes (metres) keyed by host city."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> dict[str, int]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        altitudes: dict[str, int] = {}
        for _, row in df.iterrows():
            try:
                altitudes[str(row["city"])] = int(row["altitude_m"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric altitude in row: {row.to_dict()}") from exc
        return altitudes
