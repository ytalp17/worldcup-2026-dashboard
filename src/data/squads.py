from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

_CANONICAL = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Curacao": "Curaçao",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "Iran": "IR Iran",
    "Ivory Coast": "Côte d'Ivoire",
    "South Korea": "Korea Republic",
    "Turkey": "Türkiye",
    "United States": "USA",
}


def canonical_team(csv_name: str) -> str:
    return _CANONICAL.get(csv_name, csv_name)


@dataclass(frozen=True)
class Player:
    number: int          # shirt number (0 if missing)
    name: str
    position: str        # raw CSV position (e.g. "Centre-Back")
    dob: str
    age: str
    club: str
    height_m: str
    foot: str
    caps: str
    goals: str
    debut: str
    market_value: str


@dataclass(frozen=True)
class Squad:
    name: str
    players: tuple[Player, ...]


def _cell(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _to_int(value) -> int:
    text = _cell(value)
    return int(text) if text.isdigit() else 0


class SquadRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Squad]:
        df = pd.read_csv(self.path, dtype=str, keep_default_na=False)
        squads: dict[str, list[Player]] = {}
        for _, row in df.iterrows():
            team = canonical_team(_cell(row["country"]))
            squads.setdefault(team, []).append(
                Player(
                    number=_to_int(row["shirt_number"]),
                    name=_cell(row["name"]),
                    position=_cell(row["position"]),
                    dob=_cell(row["date_of_birth"]),
                    age=_cell(row["age"]),
                    club=_cell(row["club"]),
                    height_m=_cell(row["height_m"]),
                    foot=_cell(row["foot"]),
                    caps=_cell(row["international_caps"]),
                    goals=_cell(row["international_goals"]),
                    debut=_cell(row["debut"]),
                    market_value=_cell(row["market_value"]),
                )
            )
        return {name: Squad(name, tuple(players)) for name, players in squads.items()}


def squad_for_team(squads: dict[str, Squad], team: str) -> Squad | None:
    return squads.get(team)
