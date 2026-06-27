from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _hist():
    return {"A": [3, 6, 7], "B": [1, 4, 10], "C": [0, 3, 3], "D": [3, 3, 4]}


def test_frame_count_is_max_matchdays():
    assert views.race_frame_count(_hist()) == 3
    assert views.race_frame_count({}) == 0


def test_race_figure_uses_cumulative_value_at_frame():
    fig = views.race_figure(_hist(), "points", frame=2)  # final matchday
    assert isinstance(fig, go.Figure)
    bar = fig.data[0]
    # bars sorted ascending -> last bar is the leader B with 10
    assert list(bar.y)[-1] == "B"
    assert list(bar.x)[-1] == 10


def test_race_figure_clamps_frame_and_labels_matchday():
    fig = views.race_figure(_hist(), "points", frame=99)
    ann = " ".join(a.text for a in fig.layout.annotations)
    assert "Matchday 3" in ann
