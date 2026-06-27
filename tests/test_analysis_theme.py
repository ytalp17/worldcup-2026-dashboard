from __future__ import annotations

from src.components.analysis import theme


def test_palette_is_the_four_spec_colors_in_order():
    assert theme.TEAM_COLORS == ["#534AB7", "#1D9E75", "#D85A30", "#378ADD"]
    assert len(theme.TEAM_FILLS) == 4
    assert all(f.startswith("rgba(") and "0.15" in f for f in theme.TEAM_FILLS)


def test_color_map_assigns_in_order_and_cycles():
    m = theme.team_color_map(["Mexico", "Brazil", "Spain", "Japan"])
    assert m["Mexico"] == "#534AB7"
    assert m["Japan"] == "#378ADD"
    # a 5th team cycles back to the first color (never KeyErrors)
    m5 = theme.team_color_map(["A", "B", "C", "D", "E"])
    assert m5["E"] == "#534AB7"


def test_plotly_layout_is_transparent_and_theme_aware():
    dark = theme.plotly_layout("dark")
    light = theme.plotly_layout("light")
    assert dark["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert dark["plot_bgcolor"] == "rgba(0,0,0,0)"
    assert dark["font"]["color"] != light["font"]["color"]


def test_defend_and_dumbbell_color_constants():
    assert theme.DEFEND_COLORS["tackles_succ"] == "#1D9E75"
    assert theme.DEFEND_COLORS["clearances"] == "#EF9F27"
    assert theme.DUMBBELL["xg"] == "#888780"
    assert theme.DUMBBELL["goals"] == "#185FA5"
