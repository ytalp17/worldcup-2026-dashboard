from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    out = []
    for t in ["A", "B", "C", "D"]:
        out.append({"team": t, "tackles_succ": 12.0, "interceptions": 6.0,
                    "clearances": 20.0, "aerials_won": 10.0, "matches_played": 2})
    return out


def test_defend_has_four_action_traces_stacked():
    fig = views.defend_figure(_recs())
    assert fig.layout.barmode == "stack"
    assert len(fig.data) == 4
    names = {tr.name for tr in fig.data}
    assert names == {"Tackles won", "Interceptions", "Clearances", "Aerials won"}


def test_defend_values_are_per90():
    fig = views.defend_figure(_recs())
    tackles = next(tr for tr in fig.data if tr.name == "Tackles won")
    assert list(tackles.y) == [6.0, 6.0, 6.0, 6.0]  # 12 / 2 matches


def test_defend_segment_colors_are_fixed():
    fig = views.defend_figure(_recs())
    by_name = {tr.name: tr.marker.color for tr in fig.data}
    assert by_name["Tackles won"] == "#1D9E75"
    assert by_name["Clearances"] == "#EF9F27"
