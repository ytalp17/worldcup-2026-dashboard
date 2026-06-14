from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

# ---- tab catalogue -------------------------------------------------------

TEAM_TABS = ["Attack & xG", "Possession & Passing", "Defense", "Discipline"]
PLAYER_TABS = ["Goals", "Assists", "Cards"]

# Team stat tabs (not Standings) -> the tournament_team_leaders key.
_TEAM_TAB_KEY = {"Attack & xG": "attack", "Possession & Passing": "possession",
                 "Defense": "defense", "Discipline": "discipline"}
# Player tabs -> the tournament_player_leaders key.
_PLAYER_TAB_KEY = {"Goals": "goals", "Assists": "assists", "Cards": "cards"}

_GRID_OPTIONS = {"suppressCellFocus": True, "rowHeight": 32, "headerHeight": 34,
                 "overlayNoRowsTemplate": "No data yet"}


def _num(header, field, width=66):
    return {"headerName": header, "field": field, "width": width,
            "sortable": True, "type": "rightAligned"}


# colDefs per (scope, tab). Player tabs lead with a # rank; team tabs lead with Team.
def _columns_for(scope, tab):
    if scope == "Players":
        rank = {"headerName": "#", "field": "rank", "width": 44, "sortable": False}
        player = {"headerName": "Player", "field": "player", "flex": 1,
                  "minWidth": 120, "sortable": True}
        team = {"headerName": "Team", "field": "team", "width": 124,
                "sortable": True, "cellRenderer": "TeamCell"}
        if tab == "Cards":
            return [rank, player, team, _num("🟨", "yellow", 50),
                    _num("🟥", "red", 50), _num("Ap", "apps", 50)]
        # Goals/Assists both rank on the single aggregated `value` field.
        return [rank, player, team, _num(tab, "value", 70), _num("Ap", "apps", 50)]

    team = {"headerName": "Team", "field": "team", "flex": 1, "minWidth": 130,
            "sortable": True, "cellRenderer": "TeamCell"}
    if tab == "Attack & xG":
        return [team, _num("Goals", "goals", 60), _num("xG", "xg", 56),
                _num("xA", "xa", 56), _num("BigCh", "big_chances", 64),
                _num("Shots", "shots", 60), _num("OnT", "shots_on", 52),
                _num("OffT", "shots_off", 54), _num("Acc%", "shot_acc", 58),
                _num("InBox", "shots_in_box", 60), _num("Blk", "shots_blocked", 50),
                _num("Cor", "corners", 50), _num("Ap", "apps", 48)]
    if tab == "Possession & Passing":
        return [team, _num("Poss%", "possession", 62), _num("Passes", "passes_total", 66),
                _num("Acc%", "pass_acc", 58), _num("Key", "key_passes", 52),
                _num("Fin3rd", "passes_final_third", 64), _num("Long", "long_passes", 56),
                _num("Crs", "crosses", 50), _num("CrsW", "crosses_succ", 56),
                _num("Drb", "dribbles", 50), _num("DrbW", "dribbles_succ", 56),
                _num("Ap", "apps", 48)]
    if tab == "Defense":
        return [team, _num("Tkl", "tackles", 52), _num("TklW", "tackles_succ", 58),
                _num("Int", "interceptions", 52), _num("Clr", "clearances", 52),
                _num("Aer", "aerials", 52), _num("AerW", "aerials_won", 58),
                _num("Saves", "gk_saves", 60), _num("Ap", "apps", 48)]
    # Discipline
    return [team, _num("🟨", "yellow", 54), _num("🟥", "red", 54),
            _num("Fouls", "fouls", 60), _num("Off", "offsides", 52), _num("Ap", "apps", 48)]


def _resolve_tab(scope, tab):
    """Fall back to a scope's first tab when `tab` isn't valid for `scope`
    (transient state right after the switch flips)."""
    valid = PLAYER_TABS if scope == "Players" else TEAM_TABS
    return tab if tab in valid else valid[0]


def tab_options(scope: str) -> list[str]:
    return PLAYER_TABS if scope == "Players" else TEAM_TABS


def tourn_columns(scope: str, tab: str) -> list[dict]:
    return _columns_for(scope, _resolve_tab(scope, tab))


def tourn_row_data(scope: str, tab: str, team_leaders: dict | None,
                   player_leaders: dict | None) -> list[dict]:
    tab = _resolve_tab(scope, tab)
    if scope == "Players":
        rows = (player_leaders or {}).get(_PLAYER_TAB_KEY[tab], [])
        return [{"rank": i + 1, **r} for i, r in enumerate(rows)]
    return list((team_leaders or {}).get(_TEAM_TAB_KEY[tab], []))


def build_tournament_drawer() -> dmc.Drawer:
    """Right-side drawer: a Team/Players scope switch over a tab control over one
    AG grid. The grid's columnDefs/rowData are driven by app callbacks."""
    scope = dmc.SegmentedControl(id="tourn-scope", value="Team",
                                 data=["Team", "Players"], size="xs", fullWidth=True)
    tabs = dmc.SegmentedControl(id="tourn-tabs", value="Attack & xG",
                                data=TEAM_TABS, size="xs", fullWidth=True)
    grid = dag.AgGrid(
        id="tourn-grid",
        columnDefs=tourn_columns("Team", "Attack & xG"),
        rowData=[],
        className="ag-theme-quartz-dark tourn-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"height": "70vh", "width": "100%"},
    )
    body = dmc.Stack([scope, tabs, grid], gap="xs")
    return dmc.Drawer(
        id="tournament-drawer",
        title="Tournament Stats",
        position="right",
        size="lg",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        classNames={"content": "filter-drawer-frosted",
                    "header": "filter-drawer-frosted-header"},
        children=[body],
    )
