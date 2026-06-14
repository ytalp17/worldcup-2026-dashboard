from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "city", "country", "official_name", "stadium_name", "location",
    "capacity", "opened", "info", "image_filename",
    "latitude", "longitude", "timezone", "tz_label",
]


@dataclass(frozen=True)
class Venue:
    """A host city joined with its stadium-detail record and image state."""

    city: str
    country: str
    lat: float
    lon: float
    official_name: str  # real stadium name, e.g. "AT&T Stadium"
    stadium_name: str  # generic FIFA name, e.g. "Dallas Stadium" (match-join key)
    location: str
    capacity: int
    opened: int
    info: str
    image_filename: str
    has_image: bool
    timezone: str  # IANA name, e.g. "America/Chicago"
    tz_label: str  # friendly label, e.g. "Central Time"
    altitude_m: int | None = None  # stadium altitude in metres, if known
    region_cluster: str | None = None
    airport_code: str | None = None

    @property
    def image_src(self) -> str:
        return f"/assets/stadiums/{self.image_filename}"


def _opt(row: pd.Series, column: str) -> str | None:
    if column not in row or pd.isna(row[column]):
        return None
    text = str(row[column]).strip()
    return text or None


class VenueRepository:
    """Loads fully-joined venue records from the consolidated venues.csv."""

    def __init__(self, csv_path: str | Path, image_dir: str | Path) -> None:
        self._csv_path = Path(csv_path)
        self._image_dir = Path(image_dir)

    def load(self) -> list[Venue]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        venues: list[Venue] = []
        for _, row in df.iterrows():
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                capacity = int(row["capacity"])
                opened = int(row["opened"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric value in row: {row.to_dict()}") from exc

            if not -90.0 <= lat <= 90.0:
                raise ValueError(f"Latitude out of range: {lat}")
            if not -180.0 <= lon <= 180.0:
                raise ValueError(f"Longitude out of range: {lon}")

            altitude = row.get("altitude_m")
            altitude_m = int(altitude) if pd.notna(altitude) else None
            image_filename = str(row["image_filename"])

            venues.append(
                Venue(
                    city=str(row["city"]),
                    country=str(row["country"]),
                    lat=lat,
                    lon=lon,
                    official_name=str(row["official_name"]),
                    stadium_name=str(row["stadium_name"]),
                    location=str(row["location"]),
                    capacity=capacity,
                    opened=opened,
                    info=str(row["info"]),
                    image_filename=image_filename,
                    has_image=(self._image_dir / image_filename).exists(),
                    timezone=str(row["timezone"]),
                    tz_label=str(row["tz_label"]),
                    altitude_m=altitude_m,
                    region_cluster=_opt(row, "region_cluster"),
                    airport_code=_opt(row, "airport_code"),
                )
            )
        return venues
