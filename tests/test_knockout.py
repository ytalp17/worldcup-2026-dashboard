from datetime import date, datetime, time

import dash_mantine_components as dmc

from src.components.knockout import (
    build_knockout_drawer,
    format_ko_datetime,
    match_card,
    render_page,
)
from src.data.bracket import build_bracket
from src.data.matches import Match


def _asset(path):
    return "/assets/" + path


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


def _texts(root):
    return [n.children for n in _walk(root)
            if isinstance(n, dmc.Text) and isinstance(n.children, str)]


def _m(number, home, away, stage, d="2026-06-28", t="19:00"):
    dt = date.fromisoformat(d)
    return Match(number=number, home=home, away=away, group="", stage=stage,
                 stadium="X", date=dt, local_time=time.fromisoformat(t),
                 kickoff_utc=datetime.fromisoformat(f"{d}T{t}:00+00:00"))


def _full_ko():
    return [
        _m(73, "Group A winners", "Group B runners-up", "Round of 32"),
        _m(74, "Group C winners", "Group D runners-up", "Round of 32"),
        _m(89, "Winner Match 73", "Winner Match 74", "Round of 16"),
        _m(97, "Group E winners", "Group F winners", "Quarter-Final"),
        _m(98, "Group G winners", "Group H winners", "Quarter-Final"),
        _m(101, "Winner Match 97", "Winner Match 98", "Semi-Final"),
        _m(103, "Runner-up Match 101", "Runner-up Match 102", "Bronze Final"),
        _m(104, "Winner Match 101", "Winner Match 102", "Final"),
    ]


def test_drawer_has_required_ids_and_title():
    drawer = build_knockout_drawer()
    assert drawer.title == "Tournament Knockout"
    ids = _ids(drawer)
    for needed in ("knockout-drawer", "knockout-body", "knockout-page",
                   "knockout-prev", "knockout-next", "knockout-dots"):
        assert needed in ids, f"missing {needed}"


def test_match_card_shows_tbd_shield_when_unresolved():
    br = build_bracket(_full_ko())
    card = match_card(br["Round of 16"][0], _asset, user_tz=None,
                      today=date(2026, 6, 27))
    texts = _texts(card)
    assert texts.count("TBD") == 2          # both slots undecided
    from dash_iconify import DashIconify
    shields = [n for n in _walk(card) if isinstance(n, DashIconify)
               and getattr(n, "className", "") == "ko-shield"]
    assert len(shields) == 2                 # a shield per undecided slot


def test_match_card_shows_team_score_and_flag_when_resolved():
    results = {73: ("Mexico", "Serbia", 2, 1)}
    br = build_bracket(_full_ko(), results=results)
    card = match_card(br["Round of 32"][0], _asset, user_tz=None,
                      today=date(2026, 6, 27))
    texts = _texts(card)
    assert "Mexico" in texts and "Serbia" in texts
    assert "2" in texts and "1" in texts
    imgs = [n for n in _walk(card) if isinstance(n, dmc.Image)]
    assert any(getattr(i, "src", "").endswith("flags/Mexico.png")
               for i in imgs)


def test_match_card_shows_venue():
    matches = [_m(73, "Group A winners", "Group B runners-up", "Round of 32")]
    # _m sets stadium="X"
    br = build_bracket(matches, venues={"X": "AT&T Stadium, Dallas"})
    card = match_card(br["Round of 32"][0], _asset, user_tz=None,
                      today=date(2026, 6, 27))
    assert "AT&T Stadium, Dallas" in _texts(card)


def test_match_card_is_clickable_when_live_match_id_known():
    from dash import html
    br = build_bracket(_full_ko(), results={73: ("Mexico", "Serbia", 2, 1)},
                       match_ids={73: 555})
    node = match_card(br["Round of 32"][0], _asset, None, date(2026, 6, 27))
    # wrapped in a clickable element carrying the open-live-modal id + match_id
    assert isinstance(node, html.Div)
    assert node.id == {"type": "open-live-modal", "index": 555}
    # the card itself is still inside
    assert any(str(getattr(n, "className", "")).split()[:1] == ["ko-card"]
               for n in _walk(node))


def test_match_card_not_clickable_without_match_id():
    br = build_bracket(_full_ko())
    node = match_card(br["Round of 16"][0], _asset, None, date(2026, 6, 27))
    assert getattr(node, "id", None) is None   # plain card, no click wrapper


def test_format_ko_datetime_relative_and_absolute():
    today = date(2026, 6, 27)
    bm_today = build_bracket([_m(73, "a", "b", "Round of 32", d="2026-06-27",
                                 t="21:00")])["Round of 32"][0]
    bm_tom = build_bracket([_m(74, "a", "b", "Round of 32", d="2026-06-28",
                               t="21:00")])["Round of 32"][0]
    bm_far = build_bracket([_m(75, "a", "b", "Round of 32", d="2026-06-30",
                              t="03:00")])["Round of 32"][0]
    assert format_ko_datetime(bm_today, None, today) == "Today, 21:00"
    assert format_ko_datetime(bm_tom, None, today) == "Tomorrow, 21:00"
    far = format_ko_datetime(bm_far, None, today)
    assert "30 Jun" in far and "03:00" in far


def test_render_page_zero_has_stage_headers_and_tie_cards():
    br = build_bracket(_full_ko())
    page = render_page(br, 0, _asset, user_tz=None, today=date(2026, 6, 27))
    texts = _texts(page)
    assert "Round of 32" in texts and "Round of 16" in texts
    # one tie: two feeder cards + one winner card => 3 cards
    cards = [n for n in _walk(page)
             if getattr(n, "className", "") == "ko-card"]
    assert len(cards) == 3


def test_render_finals_page_shows_final_and_third_place():
    br = build_bracket(_full_ko())
    page = render_page(br, 2, _asset, user_tz=None, today=date(2026, 6, 27))
    texts = _texts(page)
    assert "Final" in texts
    assert any("3rd" in t or "Third" in t for t in texts)
