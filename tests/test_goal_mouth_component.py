# tests/test_goal_mouth_component.py
import plotly.graph_objects as go
import dash_mantine_components as dmc

from src.data.live.shots import ShotRecord
from src.data.live.goal_mouth import aggregate_goal_mouth
from src.components.goal_mouth import (
    OUTCOME_COLORS, ZONE_LABEL, cell_fill_colors, zone_hover_text,
    build_goal_mouth_figure, drawer_body,
)


def _agg():
    recs = [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre"),
            ShotRecord(1, "X", "B", "20'", "Saved", "Low Centre"),
            ShotRecord(1, "X", "C", "30'", "Missed", "CloseLeft"),
            ShotRecord(1, "X", "D", "40'", "Missed", None)]
    return aggregate_goal_mouth(recs)


def test_outcome_colors_enum():
    assert OUTCOME_COLORS["Goal"] == "#1D9E75"
    assert OUTCOME_COLORS["Saved"] == "#378ADD"
    assert OUTCOME_COLORS["Blocked"] == "#888780"
    assert OUTCOME_COLORS["Post"] == "#D85A30"


def test_dominant_mode_colors_cell_by_top_outcome():
    colors = cell_fill_colors(_agg(), mode="dominant")
    # low_centre has Goal+Saved (tie broken deterministically); a non-empty cell
    # gets a color, an empty cell stays faint/transparent-ish.
    assert colors["low_centre"] != colors["high_left"]


def test_volume_mode_single_hue_varies_by_count():
    colors = cell_fill_colors(_agg(), mode="volume")
    assert colors["low_centre"] != colors["high_right"]   # count 2 vs 0


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


def test_figure_has_six_grid_traces_plus_present_margins():
    fig = build_goal_mouth_figure(_agg())
    assert isinstance(fig, go.Figure)
    zids = [t.customdata[0] for t in fig.data if t.customdata is not None]
    assert set(z for z in zids if z in ZONE_LABEL) >= set(
        ["high_left", "high_centre", "high_right",
         "low_left", "low_centre", "low_right", "close_left"])
    assert "close_high" not in zids                # absent margin not drawn


def test_empty_figure_still_has_six_grid_cells():
    fig = build_goal_mouth_figure(aggregate_goal_mouth([]))
    zids = [t.customdata[0] for t in fig.data if t.customdata is not None]
    assert sum(z in ("high_left", "high_centre", "high_right",
                     "low_left", "low_centre", "low_right") for z in zids) == 6


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
    assert any("Goal-mouth map" == t for t in texts)
    # never call it a "shot map"
    assert not any(isinstance(t, str) and "shot map" in t.lower() for t in texts)
    # honest-limitation note present
    assert any(isinstance(t, str) and "placement" in t.lower() for t in texts)
    graph = next(n for n in _walk(panel) if isinstance(n, dcc.Graph))
    assert graph.config.get("displayModeBar") is False


def test_drawer_is_left_positioned():
    drawer = build_goal_mouth_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "goal-mouth-drawer"
    assert drawer.position == "left"
