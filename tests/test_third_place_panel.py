"""Third-place ranking drawer: AG grid columns, rows and the advancing marker."""
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.third_place import (
    COL_DEFS,
    THIRD_PLACE_GRID_ID,
    build_third_place_drawer,
    third_place_rows,
)


def _row(team, points, gd=0, gf=0, played=3):
    return {"team": team, "points": points, "goal_diff": gd,
            "goals_for": gf, "played": played}


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


# 12 groups, third-placed team points decreasing A..L so ranking is deterministic.
def _standings():
    out = {}
    for i in range(12):
        letter = chr(ord("A") + i)
        out[f"Group {letter}"] = [
            _row(f"{letter}1", 100), _row(f"{letter}2", 99),
            _row(f"{letter}3", 12 - i),  # third-placed team (below the top two)
            _row(f"{letter}4", 0),
        ]
    return out


def _asset(path):
    return "/assets/" + path


class TestColDefs:
    def test_has_team_renderer_group_and_points_columns(self):
        by_field = {c.get("field"): c for c in COL_DEFS}
        assert by_field["team"]["cellRenderer"] == "TeamCell"
        assert "group" in by_field
        assert "pts" in by_field

    def test_has_status_tag_column(self):
        # A status column carries the "R32" advancing marker.
        assert any(c.get("field") == "tag" for c in COL_DEFS)


class TestRows:
    def test_one_row_per_group_ranked(self):
        rows = third_place_rows(_standings(), _asset)
        assert len(rows) == 12
        assert [r["rank"] for r in rows] == list(range(1, 13))

    def test_top_eight_tagged_r32_rest_blank(self):
        rows = third_place_rows(_standings(), _asset)
        assert [r["advance"] for r in rows[:8]] == [True] * 8
        assert all(r["tag"] == "R32" for r in rows[:8])
        assert all(not r["advance"] and r["tag"] == "" for r in rows[8:])

    def test_row_carries_group_letter_and_flag(self):
        rows = third_place_rows(_standings(), _asset)
        top = rows[0]
        assert top["group"] == "A"            # "Group A" -> "A"
        assert top["flag"] == "/assets/country_logos/A3.svg"
        assert top["pts"] == 12

    def test_resolve_team_used_for_name_and_flag(self):
        rows = third_place_rows(
            {"Group A": [_row("A1", 9), _row("A2", 6), _row("Raw", 3), _row("A4", 0)]},
            _asset, resolve_team=lambda t: "Official" if t == "Raw" else t)
        assert rows[0]["flag"] == "/assets/country_logos/Official.svg"

    def test_empty_standings_no_rows(self):
        assert third_place_rows({}, _asset) == []


class TestDrawer:
    def test_drawer_holds_grid_with_advance_rule(self):
        drawer = build_third_place_drawer()
        assert isinstance(drawer, dmc.Drawer)
        assert drawer.id == "third-place-drawer"
        grids = [n for n in _walk(drawer) if isinstance(n, dag.AgGrid)]
        assert len(grids) == 1
        assert grids[0].id == THIRD_PLACE_GRID_ID
        rules = grids[0].dashGridOptions["rowClassRules"]
        assert "tp-row--advance" in rules

    def test_drawer_is_frosted_right_side(self):
        drawer = build_third_place_drawer()
        assert drawer.position == "right"
        assert "filter-drawer-frosted" in drawer.classNames["content"]
