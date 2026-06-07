import dash_mantine_components as dmc

from src.components.leaders_card import build_leaders_card


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_leaders_card_has_header_and_segmented_control():
    card = build_leaders_card()
    assert card.className == "leaders-panel"
    texts = [n.children for n in _walk(card)
             if isinstance(n, dmc.Text) and isinstance(n.children, str)]
    assert "Leaders" in texts

    seg = next(n for n in _walk(card) if isinstance(n, dmc.SegmentedControl))
    values = [d["value"] if isinstance(d, dict) else d for d in seg.data]
    assert values == ["Goals", "Assists", "Cards"]


def test_leaders_card_has_empty_state():
    card = build_leaders_card()
    blob = " ".join(n.children for n in _walk(card)
                    if isinstance(n, dmc.Text) and isinstance(n.children, str))
    assert "matches start" in blob.lower()
