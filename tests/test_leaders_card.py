import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.leaders_card import (
    build_leaders_card,
    leaders_columns,
    leaders_row_data,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_leaders_card_has_header_and_four_tabs():
    card = build_leaders_card()
    assert card.className == "leaders-panel"
    texts = [n.children for n in _walk(card)
             if isinstance(n, dmc.Text) and isinstance(n.children, str)]
    assert "Leaders" in texts
    seg = next(n for n in _walk(card) if isinstance(n, dmc.SegmentedControl))
    values = [d["value"] if isinstance(d, dict) else d for d in seg.data]
    assert values == ["Goals", "Assists", "Cards", "Rating"]


def test_leaders_card_has_grid():
    card = build_leaders_card()
    grid = next(n for n in _walk(card) if isinstance(n, dag.AgGrid))
    assert grid.id == "leaders-grid"


def test_leaders_columns_header_reflects_tab():
    cols = leaders_columns("Assists")
    headers = [c["headerName"] for c in cols]
    assert headers == ["#", "Player", "Assists", "Apps"]
    fields = [c["field"] for c in cols]
    assert fields == ["rank", "player", "value", "apps"]


def test_leaders_row_data_picks_stat_and_adds_rank():
    leaders = {"goals": [{"player": "A", "value": 3, "apps": 2},
                         {"player": "B", "value": 1, "apps": 1}]}
    rows = leaders_row_data(leaders, "Goals")
    assert rows == [
        {"rank": 1, "player": "A", "value": 3, "apps": 2},
        {"rank": 2, "player": "B", "value": 1, "apps": 1},
    ]


def test_leaders_row_data_empty_when_no_data():
    assert leaders_row_data({}, "Goals") == []
    assert leaders_row_data(None, "Rating") == []
