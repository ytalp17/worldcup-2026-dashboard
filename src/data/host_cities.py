from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = ["City", "Country", "Stadium", "Capacity", "Latitude", "Longitude"]


@dataclass(frozen=True)
class HostCity:
    city: str
    country: str
    stadium: str
    capacity: int
    lat: float
    lon: float


class HostCityRepository:
    """Loads and validates FIFA 2026 host cities from a CSV file."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> list[HostCity]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        cities: list[HostCity] = []
        for _, row in df.iterrows():
            try:
                capacity = int(row["Capacity"])
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric value in row: {row.to_dict()}") from exc

            if not -90.0 <= lat <= 90.0:
                raise ValueError(f"Latitude out of range: {lat}")
            if not -180.0 <= lon <= 180.0:
                raise ValueError(f"Longitude out of range: {lon}")

            cities.append(
                HostCity(
                    city=str(row["City"]),
                    country=str(row["Country"]),
                    stadium=str(row["Stadium"]),
                    capacity=capacity,
                    lat=lat,
                    lon=lon,
                )
            )
        return cities
