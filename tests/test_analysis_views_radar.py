from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    base = {k: 1.0 for k in
            ["xg", "xa", "big_chances", "shots_in_box", "key_passes",
             "possession", "passes_succ", "passes_final_third", "dribbles_succ",
             "tackles_succ", "interceptions", "clearances", "aerials_won",
             "gk_saves", "crosses", "long_passes", "dribbles", "aerials"]}
    out = []
    for i, t in enumerate(["A", "B", "C", "D"]):
        r = dict(base, team=t, matches_played=2)
        r["xg"] = float(i + 1)  # vary one axis so scaling differs
        out.append(r)
    return out


def test_views_config_has_ten_entries_in_order():
    assert len(views.VIEWS) == 10
    assert [v["id"] for v in views.VIEWS][:6] == [
        "ATTACKING_THREAT", "BUILD_UP", "DEFENSIVE_WORK",
        "STYLE_FINGERPRINT", "FINISHING", "RACE"]


def test_no_radar_mixes_a_count_with_its_successful_pair():
    pairs = [("crosses", "crosses_succ"), ("dribbles", "dribbles_succ"),
             ("tackles", "tackles_succ"), ("aerials", "aerials_won"),
             ("passes_total", "passes_succ")]
    for v in views.VIEWS:
        if v["type"] != "radar":
            continue
        keys = {k for k, _l, _kind in v["metrics"]}
        for raw, succ in pairs:
            assert not (raw in keys and succ in keys), f"{v['id']} mixes {raw}+{succ}"
        assert len(v["metrics"]) <= 6


def test_radar_figure_has_one_trace_per_team_and_hidden_radial_ticks():
    view = views.VIEW_BY_ID["ATTACKING_THREAT"]
    fig = views.radar_figure(_recs(), view, theme="dark")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4
    assert all(tr.type == "scatterpolar" for tr in fig.data)
    assert fig.layout.polar.radialaxis.showticklabels is False
    assert fig.layout.polar.radialaxis.range == (0, 100)


def test_radar_hover_shows_raw_not_scaled():
    view = views.VIEW_BY_ID["ATTACKING_THREAT"]
    fig = views.radar_figure(_recs(), view, theme="dark")
    # customdata carries raw per-match values; hovertemplate references it
    assert any("customdata" in (tr.hovertemplate or "") or tr.customdata is not None
               for tr in fig.data)


def test_defensive_work_has_caveat():
    assert views.VIEW_BY_ID["DEFENSIVE_WORK"].get("caveat")
