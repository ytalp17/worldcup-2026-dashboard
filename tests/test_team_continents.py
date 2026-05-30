from pathlib import Path

import pandas as pd
import pytest

from src.data.team_continents import (
    CONTINENT_ORDER,
    TEAM_CONTINENT,
    continent_for,
    grouped_team_options,
)

MATCHES = Path(__file__).parent.parent / "assets" / "data" / "wc2026_matches.csv"


def _group_stage_teams():
    m = pd.read_csv(MATCHES)
    gs = m[m["stage"] == "Group Stage"]
    return set(pd.concat([gs["home_team"], gs["away_team"]]))


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
