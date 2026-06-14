from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Lineup slugs (the keys in estimated_starting_eleven.json) whose canonical FIFA
# name (as used everywhere else in the app — see TEAM_NAMES / src/data/squads.py)
# differs from a plain title-case of the slug.
_SLUG_TO_CANONICAL = {
    "bosnia-and-herzegovina": "Bosnia and Herzegovina",
    "cape-verde": "Cabo Verde",
    "curacao": "Curaçao",
    "dr-congo": "Congo DR",
    "iran": "IR Iran",
    "ivory-coast": "Côte d'Ivoire",
    "south-korea": "Korea Republic",
    "turkiye": "Türkiye",
    "usa": "USA",
}


def canonical_team(slug: str) -> str:
    """Canonical FIFA team name for a scrape slug. Plain slugs title-case
    (e.g. 'new-zealand' -> 'New Zealand')."""
    if slug in _SLUG_TO_CANONICAL:
        return _SLUG_TO_CANONICAL[slug]
    return slug.replace("-", " ").title()


def format_formation(digits: str) -> str:
    """'433' -> '4-3-3'."""
    return "-".join(digits)


@dataclass(frozen=True)
class StartingEleven:
    team: str                       # canonical FIFA name
    slug: str                       # scrape slug (== PNG asset filename stem)
    formation: str                  # digits only, e.g. "433"
    coach: str
    xi: tuple[tuple[str, int], ...]  # 11 × (surname, shirt number), GK first


class LineupRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, StartingEleven]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        lineups: dict[str, StartingEleven] = {}
        for slug, entry in raw.items():
            team = canonical_team(slug)
            xi = tuple((str(name), int(number)) for name, number in entry["xi"])
            lineups[team] = StartingEleven(
                team=team,
                slug=slug,
                formation=str(entry["formation"]),
                coach=str(entry.get("coach", "")),
                xi=xi,
            )
        return lineups


def lineup_for_team(
    lineups: dict[str, StartingEleven], team: str
) -> StartingEleven | None:
    return lineups.get(team)
