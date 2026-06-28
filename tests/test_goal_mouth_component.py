# tests/test_goal_mouth_component.py
import plotly.graph_objects as go
import dash_mantine_components as dmc

from src.data.live.shots import ShotRecord
from src.data.live.goal_mouth import aggregate_goal_mouth
from src.components.goal_mouth import (
    OUTCOME_COLORS, ZONE_LABEL, zone_hover_text,
    build_goal_mouth_figure, drawer_body,
)

_SIX = {"high_left", "high_centre", "high_right",
        "low_left", "low_centre", "low_right"}


def _agg():
    recs = [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre", "Spain"),
            ShotRecord(1, "X", "B", "20'", "Saved", "Low Centre", "Spain"),
            ShotRecord(1, "X", "C", "30'", "Missed", "CloseLeft", "Spain"),
            ShotRecord(1, "X", "D", "40'", "Missed", None, "Spain")]
    return aggregate_goal_mouth(recs)


def _heatmap(fig):
    return next(t for t in fig.data if t.type == "heatmap")


def test_outcome_colors_enum():
    assert OUTCOME_COLORS["Goal"] == "#1D9E75"
    assert OUTCOME_COLORS["Saved"] == "#378ADD"
    assert OUTCOME_COLORS["Blocked"] == "#888780"
    assert OUTCOME_COLORS["Post"] == "#D85A30"


def test_hover_text_has_breakdown_and_click_prompt():
    agg = aggregate_goal_mouth(
        [ShotRecord(1, "X", "P", "5'", "Saved", "Low Centre")] * 7)
    txt = zone_hover_text("low_centre", agg["zones"]["low_centre"])
    assert "Low Centre" in txt
    assert "7" in txt
    assert "click to see all 7" in txt


def test_hover_text_no_click_prompt_when_few():
    agg = _agg()
    txt = zone_hover_text("low_centre", agg["zones"]["low_centre"])  # 2 shots
    assert "click to see all" not in txt


def test_heatmap_covers_six_grid_cells_with_counts():
    fig = build_goal_mouth_figure(_agg())
    assert isinstance(fig, go.Figure)
    hm = _heatmap(fig)
    flat = [zid for row in hm.customdata for zid in row]
    assert set(flat) == _SIX                           # 2x3 grid of zone ids
    texts = [t for row in hm.text for t in row]
    assert "2" in texts                                # low_centre count shown


def test_heatmap_colorbar_legend_only_when_data():
    assert _heatmap(build_goal_mouth_figure(_agg())).showscale is True
    empty = _heatmap(build_goal_mouth_figure(aggregate_goal_mouth([])))
    assert empty.showscale is False                    # nothing to scale


def test_no_near_miss_markers_rendered():
    # Close-miss markers were removed by request — only the hit-marker scatter
    # remains (no "near-miss" trace, even when a margin shot is present).
    fig = build_goal_mouth_figure(_agg())              # CloseLeft present in agg
    assert not any(t.name == "near-miss" for t in fig.data)


def test_clickable_hit_markers_cover_the_grid():
    fig = build_goal_mouth_figure(_agg())
    hit = next(t for t in fig.data if t.name == "zone-hit")
    assert set(hit.customdata) == _SIX
    assert str(hit.marker.color).endswith("0)")        # transparent / invisible


def _grid(body):
    import dash_ag_grid as dag
    return next(n for n in _walk(body[0]) if isinstance(n, dag.AgGrid))


def test_drawer_body_renders_ag_grid_of_shots_sorted_with_opponent():
    agg = aggregate_goal_mouth([
        ShotRecord(1, "X", "Late", "80'", "Goal", "Low Centre", "Brazil"),
        ShotRecord(1, "X", "Early", "10'", "Saved", "Low Centre", "Brazil")])
    body = drawer_body("low_centre", agg)
    assert isinstance(body, list) and body
    grid = _grid(body)
    # time-sorted rows carrying the opponent ("vs <team>") of each shot
    assert [r["player"] for r in grid.rowData] == ["Early", "Late"]
    assert all(r["opponent"] == "Brazil" for r in grid.rowData)
    fields = {c["field"] for c in grid.columnDefs}
    assert {"min", "player", "opponent", "outcome"} <= fields


def test_drawer_body_outcome_column_carries_outcome_colors():
    agg = aggregate_goal_mouth(
        [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre", "Brazil")])
    grid = _grid(drawer_body("low_centre", agg))
    outcome_col = next(c for c in grid.columnDefs if c["field"] == "outcome")
    blob = str(outcome_col.get("cellStyle"))
    assert OUTCOME_COLORS["Goal"] in blob          # colors live in the column def


def test_drawer_body_grid_follows_theme():
    agg = aggregate_goal_mouth(
        [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre", "Brazil")])
    assert "ag-theme-quartz-dark" in _grid(drawer_body("low_centre", agg, True)).className
    assert "ag-theme-quartz " in _grid(
        drawer_body("low_centre", agg, False)).className + " "


# ---------------------------------------------------------------------------
# Task 7: panel + drawer constructors
# ---------------------------------------------------------------------------
from dash import dcc
from src.components.goal_mouth import (
    build_goal_mouth_panel, build_goal_mouth_drawer,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_panel_has_header_title_and_graph_no_mode_control():
    panel = build_goal_mouth_panel()
    ids = {getattr(n, "id", None) for n in _walk(panel)}
    assert "goal-mouth-graph" in ids
    assert "goal-mouth-subtitle" in ids          # on/off-target tally lives here
    # Volume/Dominant fill-mode control was removed by request.
    assert "goal-mouth-mode" not in ids
    assert not any(isinstance(n, dmc.SegmentedControl) for n in _walk(panel))
    texts = [n.children for n in _walk(panel) if isinstance(n, dmc.Text)]
    assert any("Shoot map" == t for t in texts)
    # minimal header: the "where each team's shots finished" subtitle and the
    # placement disclaimer caption were removed by request.
    assert not any(isinstance(t, str) and "where each team's shots finished" in t
                   for t in texts)
    assert not any(isinstance(t, str) and "placement" in t.lower() for t in texts)
    graph = next(n for n in _walk(panel) if isinstance(n, dcc.Graph))
    assert graph.config.get("displayModeBar") is False


def test_drawer_is_left_positioned():
    drawer = build_goal_mouth_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "goal-mouth-drawer"
    assert drawer.position == "left"


def test_drawer_has_no_overlay_so_zones_stay_clickable():
    # No overlay: the goal-mouth box stays interactive while the drawer is open,
    # so clicking another zone replaces the contents in one click and the only
    # dismissals are re-click / close (per spec).
    drawer = build_goal_mouth_drawer()
    assert drawer.withOverlay is False
