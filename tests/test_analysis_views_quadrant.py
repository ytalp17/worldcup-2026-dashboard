from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "A", "xg": 6.0, "goals": 6, "shots_on": 10, "shots_off": 8, "shots_blocked": 2},
        {"team": "B", "xg": 2.0, "goals": 1, "shots_on": 5, "shots_off": 4, "shots_blocked": 1},
        {"team": "C", "xg": 4.0, "goals": 3, "shots_on": 8, "shots_off": 6, "shots_blocked": 2},
        {"team": "D", "xg": 3.0, "goals": 4, "shots_on": 7, "shots_off": 5, "shots_blocked": 0},
    ]


def test_quadrant_one_point_per_team():
    fig = views.quadrant_figure(_recs())
    pts = [tr for tr in fig.data if tr.type == "scatter"]
    total_markers = sum(len(tr.x) for tr in pts)
    assert total_markers == 4


def test_quadrant_has_crosshair_lines():
    fig = views.quadrant_figure(_recs())
    # two reference lines (median/mean crosshair) added as shapes
    assert len(fig.layout.shapes) >= 2
