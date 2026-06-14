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


def _load_team_managers(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    if "coach" not in df.columns:
        return {}
    return {
        str(row["team"]): str(row["coach"]).strip()
        for _, row in df.iterrows()
        if str(row["coach"]).strip()
    }


def _load_team_ranks(csv_path: Path = _CSV_PATH) -> dict[str, int]:
    df = pd.read_csv(csv_path)
    if "fifa_rank" not in df.columns:
        return {}
    return {
        str(row["team"]): int(row["fifa_rank"])
        for _, row in df.iterrows()
        if pd.notna(row["fifa_rank"])
    }


# Team -> continent / FIFA code / head coach / FIFA rank, from assets/data/teams.csv.
TEAM_CONTINENT: dict[str, str] = _load_team_continents()
TEAM_CODE: dict[str, str] = _load_team_codes()
TEAM_MANAGER: dict[str, str] = _load_team_managers()
TEAM_FIFA_RANK: dict[str, int] = _load_team_ranks()


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


def manager_for(team: str) -> str | None:
    """Head coach for a team, or None when unknown (rendered as a placeholder)."""
    return TEAM_MANAGER.get(team)


def fifa_rank_for(team: str) -> int | None:
    """FIFA world ranking for a team, or None when unknown."""
    return TEAM_FIFA_RANK.get(team)


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
