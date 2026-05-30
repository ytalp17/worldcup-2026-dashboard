from __future__ import annotations

import colorsys
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from src.data.matches import Match
from src.data.team_continents import TEAM_CONTINENT, continent_for
from src.data.venues import Venue

# Stable team order used to spread colors deterministically.
_ALL_TEAMS = sorted(TEAM_CONTINENT)


def team_color(team: str) -> str:
    """Deterministic, well-spread hex color, stable per team."""
    i = _ALL_TEAMS.index(team)  # ValueError if team unknown
    hue = (i * 137.508) % 360  # golden-angle spread
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.55, 0.6)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class FlowStop:
    lat: float
    lon: float
    stadium_name: str
    date: date
    match_number: int


def path_distance_km(stops: tuple[FlowStop, ...]) -> float:
    """Total great-circle distance along an ordered sequence of stops."""
    return sum(
        haversine_km(a.lat, a.lon, b.lat, b.lon)
        for a, b in zip(stops, stops[1:])
    )


_KM_TO_MILES = 0.621371


def format_distance(km: float) -> str:
    """Human-readable distance, e.g. '1,840 km / 1,143 mi'."""
    miles = km * _KM_TO_MILES
    return f"{round(km):,} km / {round(miles):,} mi"


@dataclass(frozen=True)
class TeamFlow:
    team: str
    continent: str
    color: str
    stops: tuple[FlowStop, ...]
    distance_km: float = 0.0


def build_team_flows(
    matches: list[Match],
    venues: list[Venue],
    distances: dict[str, float] | None = None,
) -> dict[str, TeamFlow]:
    venue_by_name = {v.stadium_name: v for v in venues}
    by_team: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if m.stage != "Group Stage":
            continue
        by_team[m.home].append(m)
        by_team[m.away].append(m)

    distances = distances or {}
    flows: dict[str, TeamFlow] = {}
    for team, team_matches in by_team.items():
        stops: list[FlowStop] = []
        for m in sorted(team_matches, key=lambda x: (x.date, x.number)):
            venue = venue_by_name.get(m.stadium)
            if venue is None:
                raise ValueError(f"No venue for stadium {m.stadium!r}")
            stops.append(FlowStop(venue.lat, venue.lon, m.stadium, m.date, m.number))
        flows[team] = TeamFlow(
            team,
            continent_for(team),
            team_color(team),
            tuple(stops),
            distances.get(team, 0.0),
        )
    return flows
