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
    recs = [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre"),
            ShotRecord(1, "X", "B", "20'", "Saved", "Low Centre"),
            ShotRecord(1, "X", "C", "30'", "Missed", "CloseLeft"),
            ShotRecord(1, "X", "D", "40'", "Missed", None)]
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


def test_near_miss_markers_only_for_present_margins():
    fig = build_goal_mouth_figure(_agg())              # only CloseLeft present
    near = next((t for t in fig.data if t.name == "near-miss"), None)
    assert near is not None
    assert set(near.customdata) == {"close_left"}


def test_dominant_mode_uses_categorical_outcome_colorbar():
    hm = _heatmap(build_goal_mouth_figure(_agg(), mode="dominant"))
    assert hm.colorbar.ticktext
    assert set(hm.colorbar.ticktext) <= set(OUTCOME_COLORS)


def test_clickable_hit_markers_cover_the_grid():
    fig = build_goal_mouth_figure(_agg())
    hit = next(t for t in fig.data if t.name == "zone-hit")
    assert set(hit.customdata) == _SIX
    assert str(hit.marker.color).endswith("0)")        # transparent / invisible


def test_drawer_body_lists_shots_sorted_with_color():
    agg = aggregate_goal_mouth([
        ShotRecord(1, "X", "Late", "80'", "Goal", "Low Centre"),
        ShotRecord(1, "X", "Early", "10'", "Saved", "Low Centre")])
    body = drawer_body("low_centre", agg)
    assert isinstance(body, list) and body
    # flatten text content to confirm order + presence
    blob = str([c.to_plotly_json() for c in body])
    assert blob.index("Early") < blob.index("Late")
    assert "Low Centre" in blob


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


def test_panel_has_header_title_mode_control_and_graph():
    panel = build_goal_mouth_panel()
    ids = {getattr(n, "id", None) for n in _walk(panel)}
    assert "goal-mouth-graph" in ids
    assert "goal-mouth-mode" in ids
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
