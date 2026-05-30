from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "match_number",
    "home_team",
    "away_team",
    "group",
    "stage",
    "stadium",
    "match_date",
]


@dataclass(frozen=True)
class Match:
    number: int
    home: str
    away: str
    group: str  # "" for knockout stages
    stage: str
    stadium: str  # generic FIFA stadium name, e.g. "Dallas Stadium"
    date: date


class MatchRepository:
    """Loads and validates the FIFA 2026 match schedule from a CSV file."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> list[Match]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        matches: list[Match] = []
        for _, row in df.iterrows():
            try:
                number = int(row["match_number"])
                match_date = date.fromisoformat(str(row["match_date"]).strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Bad match row: {row.to_dict()}") from exc

            group = "" if pd.isna(row["group"]) else str(row["group"]).strip()
            matches.append(
                Match(
                    number=number,
                    home=str(row["home_team"]),
                    away=str(row["away_team"]),
                    group=group,
                    stage=str(row["stage"]),
                    stadium=str(row["stadium"]),
                    date=match_date,
                )
            )
        return matches


def is_placeholder(team: str) -> bool:
    """True for not-yet-decided knockout slots (e.g. 'Winner Match 74',
    'Group A runners-up') rather than a confirmed national team."""
    low = team.strip().lower()
    return (
        low.startswith("group ")
        or "winner" in low
        or "runner" in low
        or "third place" in low
    )


def matches_by_stadium(matches: list[Match]) -> dict[str, list[Match]]:
    """Group matches by their (generic) stadium name, each list sorted by
    date then match number."""
    grouped: dict[str, list[Match]] = {}
    for match in matches:
        grouped.setdefault(match.stadium, []).append(match)
    for bucket in grouped.values():
        bucket.sort(key=lambda m: (m.date, m.number))
    return grouped
