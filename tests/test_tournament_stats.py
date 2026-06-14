import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.tournament_stats import (
    build_tournament_drawer,
    tab_options,
    tourn_columns,
    tourn_row_data,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_drawer_has_scope_switch_tabs_and_grid():
    drawer = build_tournament_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "tournament-drawer"
    seg_ids = {n.id for n in _walk(drawer) if isinstance(n, dmc.SegmentedControl)}
    assert {"tourn-scope", "tourn-tabs"} <= seg_ids
    grid = next(n for n in _walk(drawer) if isinstance(n, dag.AgGrid))
    assert grid.id == "tourn-grid"


def test_tab_options_per_scope():
    assert tab_options("Team") == ["Attack & xG", "Possession & Passing",
                                    "Defense", "Discipline"]
    assert tab_options("Players") == ["Goals", "Assists", "Cards"]


def test_player_columns_and_rows():
    cols = tourn_columns("Players", "Goals")
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "Goals", "Ap"]
    leaders = {"goals": [{"player": "A", "team": "USA", "value": 3, "apps": 2}]}
    rows = tourn_row_data("Players", "Goals", {}, leaders)
    assert rows == [{"rank": 1, "player": "A", "team": "USA", "value": 3, "apps": 2}]


def test_player_cards_columns_split_yellow_red():
    cols = tourn_columns("Players", "Cards")
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "🟨", "🟥", "Ap"]


def test_team_attack_rows_passthrough():
    cols = tourn_columns("Team", "Attack & xG")
    assert cols[0]["headerName"] == "Team"
    tl = {"attack": [{"team": "USA", "goals": 5, "xg": 2.0, "apps": 2}]}
    rows = tourn_row_data("Team", "Attack & xG", tl, {})
    assert rows[0]["team"] == "USA" and rows[0]["goals"] == 5


def test_invalid_tab_for_scope_falls_back_to_first():
    cols = tourn_columns("Players", "Defense")           # Defense is a Team tab
    assert [c["headerName"] for c in cols][:2] == ["#", "Player"]   # fell back to Goals
    rows = tourn_row_data("Players", "Defense", {}, {})
    assert rows == []


def test_removed_standings_tab_falls_back_to_first_team_tab():
    # "Standings" is no longer a Team tab; it resolves to the first team tab
    # (Attack & xG), which is empty without team-leader data.
    cols = tourn_columns("Team", "Standings")
    assert cols[0]["headerName"] == "Team"
    assert tourn_row_data("Team", "Standings", {}, {}) == []


def test_empty_inputs_give_empty_rows():
    assert tourn_row_data("Team", "Attack & xG", {}, {}) == []
    assert tourn_row_data("Players", "Goals", {}, {}) == []
