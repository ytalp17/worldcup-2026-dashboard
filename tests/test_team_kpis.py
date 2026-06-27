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


def test_kpi_cards_has_eight_with_real_and_placeholder_values():
    cards = kpi_cards(REAL)
    assert len(cards) == 8
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
    # every card's className starts with "stat-card" (some carry width modifiers)
    cards = [n for n in _walk(strip)
             if isinstance(getattr(n, "className", None), str)
             and n.className.split()[0:1] == ["stat-card"]]
    assert len(cards) == 8


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


def _header_label(card):
    # the header label is the first Text in the card (inside _head, possibly
    # wrapped in a Tooltip)
    return _texts(card)[0]


def test_kpi_cards_are_in_spec_order():
    cards = kpi_cards(REAL)
    assert [_header_label(c) for c in cards] == [
        "Value", "Avg age", "Avg height", "Foot Preference",
        "FIFA rank", "Form", "Federation", "Manager"]


def test_foot_card_header_renamed_to_foot_preference():
    cards = kpi_cards(REAL)
    headers = [_header_label(c) for c in cards]
    assert "Foot Preference" in headers
    assert "Foot" not in headers   # old standalone label is gone


def test_every_card_header_has_a_nonempty_tooltip():
    cards = kpi_cards(REAL)
    for c in cards:
        tips = [n for n in _walk(c) if isinstance(n, dmc.Tooltip)]
        assert tips, f"{_header_label(c)} card has no tooltip"
        assert all(isinstance(t.label, str) and t.label.strip() for t in tips)


def _form_dots(card_or_cards):
    cards = card_or_cards if isinstance(card_or_cards, list) else [card_or_cards]
    return [n for c in cards for n in _walk(c)
            if isinstance(getattr(n, "className", None), str)
            and n.className.startswith("form-dot")]


def _form_card(cards):
    return next(c for c in cards if _header_label(c) == "Form")


def test_form_card_renders_five_slots_padded_with_empties():
    cards = kpi_cards(REAL, form=["W", "D", "L"])
    dots = _form_dots(_form_card(cards))
    assert len(dots) == 5
    classes = [d.className for d in dots]
    assert "form-dot--w" in classes[0]
    assert "form-dot--d" in classes[1]
    assert "form-dot--l" in classes[2]
    # the two unplayed slots are hollow
    assert classes[3].endswith("form-dot--empty")
    assert classes[4].endswith("form-dot--empty")


def test_form_card_all_empty_when_no_games_played():
    cards = kpi_cards(REAL)  # default form=()
    dots = _form_dots(_form_card(cards))
    assert len(dots) == 5
    assert all(d.className.endswith("form-dot--empty") for d in dots)


def test_form_card_orders_chronologically_left_to_right():
    cards = kpi_cards(REAL, form=["L", "W"])
    dots = _form_dots(_form_card(cards))
    assert "form-dot--l" in dots[0].className   # oldest on the left
    assert "form-dot--w" in dots[1].className   # most recent next


def test_form_card_has_tooltip():
    cards = kpi_cards(REAL, form=["W"])
    tips = [n for n in _walk(_form_card(cards)) if isinstance(n, dmc.Tooltip)]
    assert tips and all(t.label.strip() for t in tips)


def test_width_modifiers_keep_federation_and_manager_unmodified():
    # Federation & Manager keep the base flex (no width modifier); the new Form
    # box gets extra room and the five data boxes give it up.
    cards = kpi_cards(REAL)
    by_label = {_header_label(c): c.className for c in cards}
    assert by_label["Form"].split() == ["stat-card", "stat-card--form"]
    assert by_label["Federation"] == "stat-card"
    assert by_label["Manager"] == "stat-card"
    for narrow in ("Value", "Avg age", "Avg height", "Foot Preference",
                   "FIFA rank"):
        assert "stat-card--narrow" in by_label[narrow]


def test_federation_card_shows_continent_on_third_line():
    stats = TeamStats(
        avg_age=29.8, avg_height=1.84, squad_value=1, value_display="€1M",
        foot_right_pct=80, foot_left_pct=15, squad_size=26,
        confederation="CONMEBOL",
        confederation_logo="/assets/confederation_logos/CONMEBOL.svg",
        confederation_region="South America",
    )
    all_text = " ".join(t for c in kpi_cards(stats) for t in _texts(c))
    assert "South America" in all_text
