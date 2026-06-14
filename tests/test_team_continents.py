from pathlib import Path

import pandas as pd
import pytest

from src.data.team_continents import (
    CONTINENT_ORDER,
    TEAM_CODE,
    TEAM_CONTINENT,
    code_for,
    continent_for,
    grouped_team_options,
)

MATCHES = Path(__file__).parent.parent / "assets" / "data" / "matches.csv"


def _group_stage_teams():
    m = pd.read_csv(MATCHES)
    gs = m[m["stage"] == "Group Stage"]
    return set(pd.concat([gs["home_team"], gs["away_team"]]))


def test_mapping_is_sourced_from_csv():
    csv_path = Path(__file__).parent.parent / "assets" / "data" / "teams.csv"
    df = pd.read_csv(csv_path)
    assert {"team", "continent", "code"} <= set(df.columns)
    from_csv = {str(r["team"]): str(r["continent"]) for _, r in df.iterrows()}
    assert TEAM_CONTINENT == from_csv


def test_all_group_stage_teams_have_a_continent():
    teams = _group_stage_teams()
    assert len(teams) == 48
    missing = [t for t in teams if t not in TEAM_CONTINENT]
    assert missing == []


def test_continents_are_from_the_known_set():
    assert set(TEAM_CONTINENT.values()) <= set(CONTINENT_ORDER)


def test_continent_for_known_and_unknown():
    assert continent_for("Brazil") == "South America"
    assert continent_for("Japan") == "Asia"
    with pytest.raises(ValueError):
        continent_for("Atlantis")


def test_grouped_options_shape_and_order():
    options = grouped_team_options(["Brazil", "France", "USA", "Japan"])
    groups = [g["group"] for g in options]
    assert groups == [c for c in CONTINENT_ORDER if c in groups]
    sa = next(g for g in options if g["group"] == "South America")
    assert sa["items"] == [{"value": "Brazil", "label": "Brazil"}]


def test_code_for_known_and_unknown():
    assert code_for("Korea Republic") == "KOR"
    assert code_for("USA") == "USA"
    assert code_for("Côte d'Ivoire") == "CIV"
    with pytest.raises(ValueError):
        code_for("Atlantis")


def test_team_code_map_covers_all_teams():
    assert len(TEAM_CODE) == 48
    assert all(len(c) == 3 for c in TEAM_CODE.values())
