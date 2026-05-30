from __future__ import annotations

# Each FIFA 2026 host city mapped to its (IANA timezone, friendly label).
CITY_TIMEZONES: dict[str, tuple[str, str]] = {
    "New York/New Jersey": ("America/New_York", "Eastern Time"),
    "Boston": ("America/New_York", "Eastern Time"),
    "Philadelphia": ("America/New_York", "Eastern Time"),
    "Atlanta": ("America/New_York", "Eastern Time"),
    "Miami": ("America/New_York", "Eastern Time"),
    "Toronto": ("America/Toronto", "Eastern Time"),
    "Dallas": ("America/Chicago", "Central Time"),
    "Houston": ("America/Chicago", "Central Time"),
    "Kansas City": ("America/Chicago", "Central Time"),
    "Mexico City": ("America/Mexico_City", "Central Time"),
    "Monterrey": ("America/Monterrey", "Central Time"),
    "Guadalajara": ("America/Mexico_City", "Central Time"),
    "Seattle": ("America/Los_Angeles", "Pacific Time"),
    "San Francisco": ("America/Los_Angeles", "Pacific Time"),
    "Los Angeles": ("America/Los_Angeles", "Pacific Time"),
    "Vancouver": ("America/Vancouver", "Pacific Time"),
}


def timezone_for(city: str) -> tuple[str, str]:
    """Return (IANA name, friendly label) for a host city.

    Raises ValueError for an unknown city.
    """
    try:
        return CITY_TIMEZONES[city]
    except KeyError as exc:
        raise ValueError(f"No timezone mapped for city {city!r}") from exc
