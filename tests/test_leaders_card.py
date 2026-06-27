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


def test_leaders_card_has_header_and_three_tabs():
    card = build_leaders_card()
    assert card.className == "leaders-panel"
    texts = [n.children for n in _walk(card)
             if isinstance(n, dmc.Text) and isinstance(n.children, str)]
    assert "Team Leaders" in texts
    seg = next(n for n in _walk(card) if isinstance(n, dmc.SegmentedControl))
    values = [d["value"] if isinstance(d, dict) else d for d in seg.data]
    assert values == ["Goals", "Assists", "Cards"]


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
        {"rank": 1, "player": "A", "value": 3, "apps": 2, "top3": True},
        {"rank": 2, "player": "B", "value": 1, "apps": 1, "top3": True},
    ]


def test_cards_columns_split_yellow_and_red():
    cols = leaders_columns("Cards")
    headers = [c["headerName"] for c in cols]
    assert headers == ["#", "Player", "🟨", "🟥", "Apps"]
    fields = [c["field"] for c in cols]
    assert fields == ["rank", "player", "yellow", "red", "apps"]


def test_cards_row_data_carries_yellow_and_red():
    leaders = {"cards": [{"player": "A", "value": 3, "yellow": 1, "red": 1,
                          "apps": 2}]}
    rows = leaders_row_data(leaders, "Cards")
    assert rows == [{"rank": 1, "player": "A", "yellow": 1, "red": 1, "apps": 2,
                     "top3": False}]


def test_leaders_row_data_empty_when_no_data():
    assert leaders_row_data({}, "Goals") == []
    assert leaders_row_data(None, "Cards") == []


def test_top3_marks_on_goals_and_assists_only_top_three():
    leaders = {"goals": [{"player": p, "value": 5 - i, "apps": 3}
                         for i, p in enumerate("ABCD")]}
    rows = leaders_row_data(leaders, "Goals")
    assert [r["top3"] for r in rows] == [True, True, True, False]
    # Assists tab marks the same way
    leaders_a = {"assists": [{"player": "X", "value": 2, "apps": 1}]}
    assert leaders_row_data(leaders_a, "Assists")[0]["top3"] is True


def test_no_top3_marks_on_cards_tab():
    leaders = {"cards": [{"player": p, "value": 1, "yellow": 1, "red": 0,
                          "apps": 2} for p in "ABC"]}
    rows = leaders_row_data(leaders, "Cards")
    assert all(r["top3"] is False for r in rows)


def test_grid_has_top3_row_class_rule():
    from src.components.leaders_card import _GRID_OPTIONS
    rules = _GRID_OPTIONS["rowClassRules"]
    assert "leaders-row--top3" in rules
    assert "top3" in rules["leaders-row--top3"]
