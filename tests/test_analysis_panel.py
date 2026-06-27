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
    for needed in ["analysis-panel", "analysis-graph", "analysis-title",
                   "analysis-caption", "analysis-caveat", "analysis-dots",
                   "analysis-prev", "analysis-next", "analysis-race-controls",
                   "analysis-race-metric", "analysis-race-replay",
                   "analysis-view-index", "analysis-race-frame",
                   "analysis-race-interval", "analysis-expand",
                   "analysis-modal", "analysis-modal-graph",
                   "analysis-modal-prev", "analysis-modal-next",
                   "analysis-modal-dots"]:
        assert needed in ids, f"missing {needed}"


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
