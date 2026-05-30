from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.data.host_cities import HostCity
from src.data.stadiums import Stadium


@dataclass(frozen=True)
class Venue:
    """A host city joined with its stadium-detail record and image state."""

    city: str
    country: str
    lat: float
    lon: float
    official_name: str  # real stadium name, e.g. "AT&T Stadium"
    location: str
    capacity: int
    opened: int
    info: str
    image_filename: str
    has_image: bool

    @property
    def image_src(self) -> str:
        return f"/assets/stadiums/{self.image_filename}"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[/\-]", " ", text.lower())).strip()


def build_venues(
    cities: list[HostCity],
    stadiums: list[Stadium],
    image_dir: str | Path,
) -> list[Venue]:
    """Join host cities to stadium details by matching the host-city name
    against the stadium name (each stadium name embeds its host city).

    Raises ValueError if any city matches zero or more than one stadium.
    """
    image_dir = Path(image_dir)
    normalized = [(_normalize(s.name), s) for s in stadiums]

    venues: list[Venue] = []
    for city in cities:
        key = _normalize(city.city)
        matches = [s for name, s in normalized if key in name]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one stadium for city {city.city!r}, "
                f"found {len(matches)}"
            )
        stadium = matches[0]
        venues.append(
            Venue(
                city=city.city,
                country=city.country,
                lat=city.lat,
                lon=city.lon,
                official_name=city.stadium,
                location=stadium.location,
                capacity=stadium.capacity,
                opened=stadium.opened,
                info=stadium.info,
                image_filename=stadium.image_filename,
                has_image=(image_dir / stadium.image_filename).exists(),
            )
        )
    return venues
