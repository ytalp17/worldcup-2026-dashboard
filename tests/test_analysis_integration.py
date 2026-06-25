from __future__ import annotations

import plotly.graph_objects as go

import app as appmod
from src.data.analysis import accessors
from src.data.groups import build_groups
from src.components.analysis import views
from tests.fixtures.analysis import sample


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


def test_layout_mounts_analysis_panel_inside_map_card():
    layout = appmod.app.layout
    # Some components use dict IDs (pattern-matching); collect as strings to
    # avoid TypeError when building the set.
    ids = set()
    for n in _walk(layout):
        raw = getattr(n, "id", None)
        if raw is not None:
            ids.add(raw if not isinstance(raw, dict) else str(raw))
    assert "analysis-panel" in ids
    assert "map-container" in ids  # map still mounted


def test_every_view_renders_in_both_themes(tmp_path, monkeypatch):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    for dark in (True, False):
        for vi in range(len(views.VIEWS)):
            fig, title, *_ = appmod.analysis_render(
                view_index=vi, race_metric="conceded", carousel_index=0,
                dark=dark, frame=1)
            assert isinstance(fig, go.Figure), (
                f"view {vi} ({views.VIEWS[vi]['id']}) dark={dark} did not return a Figure"
            )
            assert title, f"view {vi} returned empty title (dark={dark})"


def test_team_colors_consistent_across_views(tmp_path, monkeypatch):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    recs = accessors.get_group_aggregates(sample.SAMPLE_GROUP)
    cmap = views.theme.team_color_map([r["team"] for r in recs])
    # Mexico is first in seeding order -> first palette color, everywhere
    assert cmap["Mexico"] == "#534AB7"
