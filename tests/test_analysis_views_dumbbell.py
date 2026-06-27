from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "Over", "goals": 5, "xg": 2.0, "matches_played": 3, "shots_on": 12},
        {"team": "Under", "goals": 1, "xg": 4.0, "matches_played": 3, "shots_on": 10},
        {"team": "Even", "goals": 3, "xg": 3.0, "matches_played": 3, "shots_on": 9},
    ]


def test_dumbbell_sorted_by_goals_minus_xg():
    fig = views.dumbbell_figure(_recs())
    # y category order should put the biggest (goals-xg) last so it renders on top
    order = list(fig.layout.yaxis.categoryarray)
    assert order[-1] == "Over"
    assert order[0] == "Under"


def test_dumbbell_connector_color_encodes_over_under():
    fig = views.dumbbell_figure(_recs())
    # connector line traces carry the green/orange colors
    line_colors = [tr.line.color for tr in fig.data if tr.mode == "lines"]
    assert "#1D9E75" in line_colors   # over/equal -> green
    assert "#D85A30" in line_colors   # under -> orange


def test_dumbbell_uses_raw_values():
    fig = views.dumbbell_figure(_recs())
    xs = [x for tr in fig.data for x in (tr.x or [])]
    assert 5 in xs and 2.0 in xs   # raw goals + raw xg present, unscaled
