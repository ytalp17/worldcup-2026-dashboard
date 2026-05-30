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

        def _require_str(value: object, column: str) -> str:
            """Return stripped string or raise ValueError for blank/NaN values."""
            if pd.isna(value):
                raise ValueError(f"Missing value in column '{column}'")
            text = str(value).strip()
            if not text:
                raise ValueError(f"Blank value in column '{column}'")
            return text

        cities: list[HostCity] = []
        for _, row in df.iterrows():
            city = _require_str(row["City"], "City")
            country = _require_str(row["Country"], "Country")
            stadium = _require_str(row["Stadium"], "Stadium")

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
                    city=city,
                    country=country,
                    stadium=stadium,
                    capacity=capacity,
                    lat=lat,
                    lon=lon,
                )
            )
        return cities
