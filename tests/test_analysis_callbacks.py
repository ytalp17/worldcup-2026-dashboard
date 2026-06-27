from __future__ import annotations

import app as appmod
from src.data.analysis import accessors
from src.data.groups import build_groups
from tests.fixtures.analysis import sample


def _wire(tmp_path):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    return groups


def test_render_returns_figure_and_metadata_for_radar(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    fig, title, caption, caveat, dots_children, race_style = appmod.analysis_render(
        view_index=0, race_metric="points", carousel_index=0, dark=True, frame=0)
    assert fig.data  # has traces
    assert "Attacking" in title
    assert race_style == {"display": "none"}  # not the RACE view


def test_render_shows_race_controls_on_race_view(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    *_, race_style = appmod.analysis_render(
        view_index=5, race_metric="points", carousel_index=0, dark=True, frame=0)
    assert race_style.get("display") != "none"


def test_render_goals_conceded_adds_direction_caveat(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    _fig, _t, _c, caveat, *_ = appmod.analysis_render(
        view_index=5, race_metric="conceded", carousel_index=0, dark=True, frame=0)
    assert "lower is better" in caveat.lower()


def test_next_frame_stops_at_last():
    assert appmod.analysis_next_frame(0, 3) == (1, False)
    assert appmod.analysis_next_frame(2, 3) == (2, True)  # clamp + disable at end
    assert appmod.analysis_next_frame(0, 1) == (0, True)   # single matchday: stop immediately
    assert appmod.analysis_next_frame(0, 2) == (1, True)   # two matchdays: step once, then stop
