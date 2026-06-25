from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "A", "passes_total": 500.0, "passes_succ": 450.0, "passes_final_third": 80.0},
        {"team": "B", "passes_total": 300.0, "passes_succ": 240.0, "passes_final_third": 40.0},
        {"team": "C", "passes_total": 400.0, "passes_succ": 360.0, "passes_final_third": 70.0},
        {"team": "D", "passes_total": 350.0, "passes_succ": 280.0, "passes_final_third": 35.0},
    ]


def test_bubble_size_encodes_accuracy():
    fig = views.bubble_figure(_recs())
    tr = fig.data[0]
    # marker sizes proportional to accuracy %, A (90%) larger than B (80%)
    assert tr.marker.size[0] > tr.marker.size[1]


def test_build_figure_dispatches_by_type():
    radar = views.build_figure(views.VIEW_BY_ID["ATTACKING_THREAT"],
                               records=[dict(team=t, matches_played=1, xg=1.0, xa=1.0,
                                             big_chances=1, shots_in_box=1, key_passes=1)
                                        for t in "ABCD"])
    assert isinstance(radar, go.Figure)
    race = views.build_figure(views.VIEW_BY_ID["RACE"],
                              history={"A": [1, 2], "B": [0, 3]},
                              race_metric="points", frame=1)
    assert isinstance(race, go.Figure)


def test_bubble_empty_records_returns_empty_figure_without_crashing():
    fig = views.bubble_figure([])
    assert len(fig.data) == 0
