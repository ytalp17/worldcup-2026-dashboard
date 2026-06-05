import dash_ag_grid as dag

from src.components.group_table import build_group_panel, group_rows
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
    assert {"group-grid", "group-table-title", "group-extra"} <= ids

    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    team_col = next(c for c in grid.columnDefs if c.get("field") == "team")
    assert team_col["cellRenderer"] == "TeamCell"
    assert len(grid.rowData) == 4


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
