from __future__ import annotations

from pathlib import Path

import pandas as pd

CONTINENT_ORDER = [
    "North America",
    "South America",
    "Europe",
    "Africa",
    "Asia",
    "Oceania",
]

_CSV_PATH = Path(__file__).resolve().parents[2] / "assets" / "data" / "teams.csv"


def _load_team_continents(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    missing = [c for c in ("team", "continent") if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    return {str(row["team"]): str(row["continent"]) for _, row in df.iterrows()}


def _load_team_codes(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    if "code" not in df.columns:
        raise ValueError("Missing expected column: code")
    return {str(row["team"]): str(row["code"]) for _, row in df.iterrows()}


# Team -> continent / FIFA code, sourced from assets/data/teams.csv.
TEAM_CONTINENT: dict[str, str] = _load_team_continents()
TEAM_CODE: dict[str, str] = _load_team_codes()


def continent_for(team: str) -> str:
    try:
        return TEAM_CONTINENT[team]
    except KeyError as exc:
        raise ValueError(f"No continent mapped for team {team!r}") from exc


def code_for(team: str) -> str:
    try:
        return TEAM_CODE[team]
    except KeyError as exc:
        raise ValueError(f"No FIFA code mapped for team {team!r}") from exc


def grouped_team_options(teams: list[str]) -> list[dict]:
    """DMC MultiSelect grouped data, continents in CONTINENT_ORDER, teams sorted."""
    options: list[dict] = []
    for continent in CONTINENT_ORDER:
        items = sorted(t for t in teams if TEAM_CONTINENT.get(t) == continent)
        if items:
            options.append(
                {"group": continent, "items": [{"value": t, "label": t} for t in items]}
            )
    return options
