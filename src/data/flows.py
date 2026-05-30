from __future__ import annotations

import colorsys
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


@dataclass(frozen=True)
class FlowStop:
    lat: float
    lon: float
    stadium_name: str
    date: date
    match_number: int


@dataclass(frozen=True)
class TeamFlow:
    team: str
    continent: str
    color: str
    stops: tuple[FlowStop, ...]


def build_team_flows(matches: list[Match], venues: list[Venue]) -> dict[str, TeamFlow]:
    venue_by_name = {v.stadium_name: v for v in venues}
    by_team: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if m.stage != "Group Stage":
            continue
        by_team[m.home].append(m)
        by_team[m.away].append(m)

    flows: dict[str, TeamFlow] = {}
    for team, team_matches in by_team.items():
        stops: list[FlowStop] = []
        for m in sorted(team_matches, key=lambda x: (x.date, x.number)):
            venue = venue_by_name.get(m.stadium)
            if venue is None:
                raise ValueError(f"No venue for stadium {m.stadium!r}")
            stops.append(FlowStop(venue.lat, venue.lon, m.stadium, m.date, m.number))
        flows[team] = TeamFlow(team, continent_for(team), team_color(team), tuple(stops))
    return flows
