import dash_ag_grid as dag

from src.components.group_table import (
    build_group_panel,
    group_rows,
    live_group_rows,
)
from src.data.groups import Group, GroupStanding


def _asset(path):  # mimic app.get_asset_url
    return "/assets/" + path


def _group():
    return Group(
        name="Group A",
        standings=(
            GroupStanding(team="Mexico"),
            GroupStanding(team="South Africa"),
            GroupStanding(team="Korea Republic"),
            GroupStanding(team="Bosnia and Herzegovina"),
        ),
    )


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_group_rows_rank_display_name_and_flag():
    rows = group_rows(_group(), _asset)
    assert [r["rank"] for r in rows] == [1, 2, 3, 4]
    # display name is remapped / ampersanded ...
    assert rows[2]["team"] == "South Korea"
    assert rows[3]["team"] == "Bosnia & Herzegovina"
    # ... but the flag url uses the RAW team name.
    assert rows[2]["flag"] == "/assets/country_logos/Korea Republic.svg"
    assert rows[0]["team"] == "Mexico"
    assert rows[0]["flag"] == "/assets/country_logos/Mexico.svg"


def test_group_rows_stats_all_zero():
    rows = group_rows(_group(), _asset)
    for r in rows:
        assert r["mp"] == r["w"] == r["d"] == r["l"] == r["gd"] == r["pts"] == 0


def test_build_group_panel_has_expected_ids_and_team_renderer():
    panel = build_group_panel(_group(), _asset)
    ids = {getattr(n, "id", None) for n in _walk(panel)}
    assert {"group-grid", "group-table-title"} <= ids

    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    team_col = next(c for c in grid.columnDefs if c.get("field") == "team")
    assert team_col["cellRenderer"] == "TeamCell"
    assert len(grid.rowData) == 4


def test_group_rows_have_empty_status_when_static():
    rows = group_rows(_group(), _asset)
    assert all(r["status"] == "" for r in rows)


def test_live_group_rows_attach_qualification_status():
    live = {"Group A": [
        {"team": "Mexico", "played": 3, "won": 3, "drawn": 0, "lost": 0,
         "goal_diff": 6, "points": 9},
        {"team": "South Korea", "played": 3, "won": 2, "drawn": 0, "lost": 1,
         "goal_diff": 2, "points": 6},
        {"team": "Bosnia", "played": 3, "won": 1, "drawn": 0, "lost": 2,
         "goal_diff": -1, "points": 3},
        {"team": "South Africa", "played": 3, "won": 0, "drawn": 0, "lost": 3,
         "goal_diff": -7, "points": 0},
    ]}
    status_map = {"Mexico": "qualified", "South Korea": "qualified",
                  "Bosnia": "eliminated", "South Africa": "eliminated"}
    rows = live_group_rows("Group A", live, _asset, status_map=status_map)
    by_raw = {r["flag"].split("/")[-1].removesuffix(".svg"): r["status"]
              for r in rows}
    # status keyed by the raw live name; flag filename uses the (resolved) name
    statuses = [r["status"] for r in rows]
    assert statuses == ["qualified", "qualified", "eliminated", "eliminated"]


def test_grid_fits_card_and_has_marker_rules():
    panel = build_group_panel(_group(), _asset)
    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    opts = grid.dashGridOptions
    assert opts["domLayout"] == "normal"   # grid fills the card (no autoHeight)
    rules = opts["rowClassRules"]
    assert "group-row--q" in rules and "group-row--e" in rules
    assert "qualified" in rules["group-row--q"]
    assert "eliminated" in rules["group-row--e"]


def test_build_group_panel_shows_group_name():
    panel = build_group_panel(_group(), _asset)
    title = next(n for n in _walk(panel) if getattr(n, "id", None) == "group-table-title")
    assert title.children == "Group A"


def test_build_group_panel_handles_none_group():
    panel = build_group_panel(None, _asset)
    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    assert grid.rowData == []
    title = next(n for n in _walk(panel) if getattr(n, "id", None) == "group-table-title")
    assert title.children == "—"


def test_live_group_rows_builds_from_snapshot():
    from src.components.group_table import live_group_rows
    live = {"Group A": [
        {"team": "Mexico", "played": 1, "won": 1, "drawn": 0, "lost": 0,
         "goal_diff": 2, "points": 3},
        {"team": "South Africa", "played": 1, "won": 0, "drawn": 0, "lost": 1,
         "goal_diff": -2, "points": 0},
    ]}
    rows = live_group_rows("Group A", live, asset_url=lambda p: "/assets/" + p)
    assert rows is not None
    assert rows[0]["rank"] == 1
    assert rows[0]["pts"] == 3
    assert rows[0]["gd"] == 2
    assert rows[0]["mp"] == 1
    assert rows[1]["team"]  # display name present
    assert "Mexico" in rows[0]["flag"]


def test_live_group_rows_resolves_team_to_official_flag_and_name():
    # The live feed uses names like "Korea Republic"/"Czech Republic" that differ
    # from the country_logos filenames; a resolver maps them to the official name
    # so the flag URL points at a real file (no 404) and the label is friendly.
    from src.components.group_table import live_group_rows
    live = {"Group A": [
        {"team": "Korea Republic", "played": 0, "won": 0, "drawn": 0, "lost": 0,
         "goal_diff": 0, "points": 0},
    ]}
    resolve = {"korea republic": "Korea Republic"}.get  # normalized -> official
    rows = live_group_rows("Group A", live, asset_url=lambda p: "/assets/" + p,
                           resolve_team=lambda t: resolve(t.lower(), t))
    assert rows[0]["flag"].endswith("country_logos/Korea Republic.svg")
    assert rows[0]["team"] == "South Korea"   # display override applied to official


def test_live_group_rows_none_when_group_absent_or_empty():
    from src.components.group_table import live_group_rows
    assert live_group_rows("Group Z", {"Group A": [{}]}, asset_url=str) is None
    assert live_group_rows("Group A", {"Group A": []}, asset_url=str) is None
    assert live_group_rows("Group A", None, asset_url=str) is None
