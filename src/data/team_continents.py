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


def _load_team_manager_nationalities(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    if "coach_nationality" not in df.columns:
        return {}
    return {
        str(row["team"]): str(row["coach_nationality"]).strip()
        for _, row in df.iterrows()
        if str(row["coach_nationality"]).strip()
    }


def _load_team_confederations(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    if "confederation" not in df.columns:
        return {}
    return {
        str(row["team"]): str(row["confederation"]).strip()
        for _, row in df.iterrows()
        if str(row["confederation"]).strip()
    }


def _load_team_manager_ages(csv_path: Path = _CSV_PATH) -> dict[str, int]:
    df = pd.read_csv(csv_path)
    if "coach_age" not in df.columns:
        return {}
    return {
        str(row["team"]): int(row["coach_age"])
        for _, row in df.iterrows()
        if pd.notna(row["coach_age"])
    }


# Team -> continent / FIFA code / head coach / coach nationality / FIFA rank.
TEAM_CONTINENT: dict[str, str] = _load_team_continents()
TEAM_CODE: dict[str, str] = _load_team_codes()
TEAM_MANAGER: dict[str, str] = _load_team_managers()
TEAM_FIFA_RANK: dict[str, int] = _load_team_ranks()
TEAM_MANAGER_NATIONALITY: dict[str, str] = _load_team_manager_nationalities()
TEAM_MANAGER_AGE: dict[str, int] = _load_team_manager_ages()
TEAM_CONFEDERATION: dict[str, str] = _load_team_confederations()

# Raw coach_nationality values are free-text ("Morocco/Belgium",
# "UK (born in Northampton)"). Reduce to a single canonical country.
_NATIONALITY_ALIASES = {"Bosnia": "Bosnia and Herzegovina"}


def _clean_nationality(raw: str) -> str:
    primary = raw.split("/")[0].split("(")[0].strip()
    return _NATIONALITY_ALIASES.get(primary, primary)


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


def manager_nationality_for(team: str) -> str | None:
    """Head coach's nationality as a single canonical country, or None."""
    raw = TEAM_MANAGER_NATIONALITY.get(team)
    return _clean_nationality(raw) if raw else None


def manager_age_for(team: str) -> int | None:
    """Head coach's age in years, or None when unknown."""
    return TEAM_MANAGER_AGE.get(team)


def confederation_for(team: str) -> str | None:
    """Team's confederation code (UEFA, CONMEBOL, ...), or None when unknown."""
    return TEAM_CONFEDERATION.get(team)


# Continent each confederation governs (mapped onto our six-continent scheme).
CONFEDERATION_CONTINENT = {
    "AFC": "Asia",
    "CAF": "Africa",
    "CONCACAF": "North America",
    "CONMEBOL": "South America",
    "OFC": "Oceania",
    "UEFA": "Europe",
}


def confederation_continent(code: str | None) -> str | None:
    """Continent governed by a confederation code, or None when unknown."""
    return CONFEDERATION_CONTINENT.get(code) if code else None


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
