from __future__ import annotations

import app as appmod


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
