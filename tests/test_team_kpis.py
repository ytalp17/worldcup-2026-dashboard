import dash_mantine_components as dmc

from src.components.team_kpis import build_kpi_strip, kpi_cards, stat_card
from src.data.team_stats import TeamStats


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


REAL = TeamStats(
    avg_age=29.8, avg_height=1.84, squad_value=32_000_000, value_display="€32M",
    foot_right_pct=81, foot_left_pct=15, squad_size=26,
)


def _texts(node):
    return [n.children for n in _walk(node)
            if isinstance(n, dmc.Text) and isinstance(n.children, str)]


def test_stat_card_renders_label_value_sub():
    card = stat_card("tabler:user", "Avg age", "29.8", sub="years")
    texts = _texts(card)
    assert "Avg age" in texts
    assert "29.8" in texts
    assert "years" in texts


def test_kpi_cards_has_seven_with_real_and_placeholder_values():
    cards = kpi_cards(REAL)
    assert len(cards) == 7
    all_text = " ".join(t for c in cards for t in _texts(c))
    # Real, computed values
    assert "29.8" in all_text
    assert "1.84" in all_text
    assert "€32M" in all_text
    # Placeholders for the three we have no data for
    assert all_text.count("—") >= 3


def test_foot_card_uses_split_bar_with_both_percentages():
    cards = kpi_cards(REAL)
    # The donut/ring is gone, replaced by a split bar.
    assert not [n for c in cards for n in _walk(c)
                if isinstance(n, dmc.RingProgress)]
    all_text = " ".join(t for c in cards for t in _texts(c))
    assert "R 81%" in all_text and "L 15%" in all_text   # both on the foot card


def test_manager_card_shows_nationality_and_flag():
    stats = TeamStats(
        avg_age=29.8, avg_height=1.84, squad_value=1, value_display="€1M",
        foot_right_pct=80, foot_left_pct=15, squad_size=26,
        manager="Carlo Ancelotti", manager_nationality="Italy",
        manager_flag="/assets/manager_flags/Italy.png",
    )
    cards = kpi_cards(stats)
    all_text = " ".join(t for c in cards for t in _texts(c))
    assert "Carlo Ancelotti" in all_text
    assert "Italy" in all_text
    imgs = [n for c in cards for n in _walk(c) if isinstance(n, dmc.Image)]
    assert any(getattr(i, "src", "") == "/assets/manager_flags/Italy.png"
               for i in imgs)


def test_manager_card_shows_age():
    stats = TeamStats(
        avg_age=29.8, avg_height=1.84, squad_value=1, value_display="€1M",
        foot_right_pct=80, foot_left_pct=15, squad_size=26,
        manager="Carlo Ancelotti", manager_nationality="Italy",
        manager_flag="/assets/manager_flags/Italy.png", manager_age=67,
    )
    all_text = " ".join(t for c in kpi_cards(stats) for t in _texts(c))
    assert "Italy" in all_text and "67 yrs" in all_text   # age carries a unit


def test_build_kpi_strip_has_id():
    strip = build_kpi_strip(REAL)
    assert strip.id == "kpi-strip"
    cards = [n for n in _walk(strip) if getattr(n, "className", "") == "stat-card"]
    assert len(cards) == 7


def test_federation_card_shows_confederation_and_logo():
    stats = TeamStats(
        avg_age=29.8, avg_height=1.84, squad_value=1, value_display="€1M",
        foot_right_pct=80, foot_left_pct=15, squad_size=26,
        confederation="CONMEBOL",
        confederation_logo="/assets/confederation_logos/CONMEBOL.svg",
    )
    cards = kpi_cards(stats)
    all_text = " ".join(t for c in cards for t in _texts(c))
    assert "CONMEBOL" in all_text
    assert "Federation" in all_text
    imgs = [n for c in cards for n in _walk(c) if isinstance(n, dmc.Image)]
    assert any(getattr(i, "src", "") == "/assets/confederation_logos/CONMEBOL.svg"
               for i in imgs)


def test_no_abroad_card():
    all_text = " ".join(t for c in kpi_cards(REAL) for t in _texts(c))
    assert "Abroad" not in all_text
