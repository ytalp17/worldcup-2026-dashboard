from __future__ import annotations

from dash import dcc

from src.components.analysis import panel


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


def _ids(root):
    return {getattr(n, "id", None) for n in _walk(root)}


def test_panel_exposes_required_ids():
    root = panel.build_analysis_panel()
    ids = _ids(root)
    for needed in ["analysis-panel", "analysis-graph",
                   "analysis-info", "analysis-info-content", "analysis-dots",
                   "analysis-prev", "analysis-next", "analysis-race-controls",
                   "analysis-race-metric", "analysis-race-replay",
                   "analysis-view-index", "analysis-race-frame",
                   "analysis-race-interval", "analysis-expand",
                   "analysis-modal", "analysis-modal-graph",
                   "analysis-modal-prev", "analysis-modal-next",
                   "analysis-modal-dots"]:
        assert needed in ids, f"missing {needed}"


def test_caption_and_caveat_text_blocks_removed_from_card():
    # The descriptive text now lives behind the header info icon, freeing the
    # card body for the figure. No standalone caption/caveat elements remain.
    ids = _ids(panel.build_analysis_panel())
    assert "analysis-caption" not in ids
    assert "analysis-caveat" not in ids


def test_header_title_text_removed():
    # The per-view chart title (e.g. "Race over matchdays") no longer sits in the
    # header; it lives in the info hover-card and the expanded-modal title.
    assert "analysis-title" not in _ids(panel.build_analysis_panel())


def test_header_has_info_hovercard():
    import dash_mantine_components as dmc
    root = panel.build_analysis_panel()
    hovercards = [n for n in _walk(root) if isinstance(n, dmc.HoverCard)]
    assert hovercards, "no HoverCard in header"
    # the hover target is the small info ActionIcon
    target_ids = {getattr(n, "id", None) for n in _walk(hovercards[0])}
    assert "analysis-info" in target_ids
    assert "analysis-info-content" in target_ids


def test_every_view_has_caption_and_info():
    from src.components.analysis import views
    for v in views.VIEWS:
        assert v.get("caption"), f"{v['id']} missing caption"
        assert v.get("info"), f"{v['id']} missing explanatory info"


def test_info_content_renders_title_caption_info_and_caveat():
    from src.components.analysis import views
    v = views.VIEW_BY_ID["DEFENSIVE_WORK"]   # this view carries a caveat
    blob = str(panel.info_content(v).to_plotly_json())
    assert v["title"] in blob
    assert v["caption"] in blob
    assert v["info"] in blob
    assert v["caveat"] in blob


def test_info_content_caveat_override_replaces_default():
    from src.components.analysis import views
    v = views.VIEW_BY_ID["RACE"]             # no default caveat
    blob = str(panel.info_content(v, caveat="lower is better; shortest bar leads")
               .to_plotly_json())
    assert "lower is better; shortest bar leads" in blob


def test_header_label_is_group_analysis():
    import dash_mantine_components as dmc
    root = panel.build_analysis_panel()
    texts = [n.children for n in _walk(root)
             if isinstance(n, dmc.Text) and isinstance(n.children, str)]
    assert "Group Analysis" in texts
    assert "Analysis" not in texts   # old bare label is gone


def test_graph_modebar_is_hidden():
    root = panel.build_analysis_panel()
    graph = next((n for n in _walk(root) if isinstance(n, dcc.Graph)), None)
    assert graph is not None, "dcc.Graph not found"
    assert graph.config.get("displayModeBar") is False


def test_dots_marks_active():
    children = panel.dots(active=2, total=10)
    assert "3 / 10" in str(children)


def test_empty_state_names_group():
    es = panel.empty_state("Group B")
    assert "Group B" in str(es.to_plotly_json())
