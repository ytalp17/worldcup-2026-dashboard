from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    out = []
    for t in ["A", "B", "C", "D"]:
        out.append({"team": t, "shots_on": 6.0, "shots_off": 8.0,
                    "shots_blocked": 2.0, "goals": 3, "matches_played": 3})
    return out


def test_funnel_has_one_funnel_per_team():
    fig = views.funnel_figure(_recs())
    funnels = [tr for tr in fig.data if tr.type == "funnel"]
    assert len(funnels) == 4


def test_funnel_stage_values_taken_on_target_goals():
    fig = views.funnel_figure(_recs())
    tr = next(tr for tr in fig.data if tr.type == "funnel")
    # shots_total = 6+8+2 = 16, on target = 6, goals = 3
    assert list(tr.x) == [16.0, 6.0, 3]
