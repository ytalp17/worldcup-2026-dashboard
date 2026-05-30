from datetime import date

import dash_mantine_components as dmc

from src.components.detail_panel import NO_MATCHES_TEXT, PLACEHOLDER_TEXT, stadium_detail
from src.data.matches import Match
from src.data.venues import Venue


def _match(number, home, away, group, stage, day):
    return Match(
        number=number,
        home=home,
        away=away,
        group=group,
        stage=stage,
        stadium="Dallas Stadium",
        date=date(2026, 6, day),
    )


def _venue(has_image: bool) -> Venue:
    return Venue(
        city="Dallas",
        country="USA",
        lat=32.7473,
        lon=-97.0945,
        official_name="AT&T Stadium",
        stadium_name="Dallas Stadium",
        location="Arlington, Texas, USA",
        capacity=94000,
        opened=2009,
        info="Dallas Stadium is a jaw-dropping example of stadium architecture.",
        image_filename="Dallas_Stadium.jpg",
        has_image=has_image,
        timezone="America/Chicago",
        tz_label="Central Time",
    )


def _walk(node):
    """Yield every component and string in a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _all_text(node) -> str:
    parts = []
    for n in _walk(node):
        if isinstance(n, str):
            parts.append(n)
        else:
            # Some visible text (e.g. TimelineItem) lives in the `title` prop.
            title = getattr(n, "title", None)
            if isinstance(title, str):
                parts.append(title)
    return " ".join(parts)


def _images(node):
    return [n for n in _walk(node) if isinstance(n, dmc.Image)]


def test_detail_with_image_renders_image_with_correct_src():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    imgs = _images(content)
    assert len(imgs) == 1
    assert imgs[0].src == "/assets/stadiums/Dallas_Stadium.jpg"


def test_detail_without_image_shows_placeholder_not_image():
    content = dmc.Box(stadium_detail(_venue(has_image=False)))
    assert _images(content) == []
    assert PLACEHOLDER_TEXT in _all_text(content)


def test_detail_shows_key_stats_and_info():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    text = _all_text(content)
    assert "94,000" in text          # capacity, formatted
    assert "2009" in text            # year opened
    assert "Arlington, Texas, USA" in text  # location
    assert "jaw-dropping" in text    # info blurb


def test_detail_shows_timezone():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    text = _all_text(content)
    assert "Central Time" in text       # friendly label
    assert "America/Chicago" in text    # IANA name


def _timelines(node):
    return [n for n in _walk(node) if isinstance(n, dmc.Timeline)]


def _timeline_items(node):
    return [n for n in _walk(node) if isinstance(n, dmc.TimelineItem)]


def test_detail_renders_matches_timeline():
    matches = [
        _match(1, "Mexico", "South Africa", "Group A", "Group Stage", 11),
        _match(89, "Winner 74", "Winner 77", "", "Round of 16", 30),
    ]
    content = dmc.Box(stadium_detail(_venue(has_image=True), matches))
    assert len(_timelines(content)) == 1
    assert len(_timeline_items(content)) == 2
    text = _all_text(content)
    assert "Mexico" in text and "South Africa" in text
    assert "Jun 11" in text          # formatted date
    assert "Group A" in text         # group label for group stage
    assert "Round of 16" in text     # stage label for knockout


def _italic_texts(node):
    return [
        n for n in _walk(node)
        if isinstance(n, dmc.Text) and getattr(n, "fs", None) == "italic"
    ]


def test_placeholder_teams_rendered_italic():
    matches = [_match(89, "Winner Match 74", "Winner Match 77", "", "Round of 16", 30)]
    content = dmc.Box(stadium_detail(_venue(has_image=True), matches))
    italic = " ".join(t.children for t in _italic_texts(content) if isinstance(t.children, str))
    assert "Winner Match 74" in italic    # original wording preserved
    assert "Winner Match 77" in italic


def test_real_teams_not_italic():
    matches = [_match(1, "Mexico", "South Africa", "Group A", "Group Stage", 11)]
    content = dmc.Box(stadium_detail(_venue(has_image=True), matches))
    italic = " ".join(t.children for t in _italic_texts(content) if isinstance(t.children, str))
    assert "Mexico" not in italic
    assert "South Africa" not in italic


def test_detail_without_matches_shows_placeholder():
    content = dmc.Box(stadium_detail(_venue(has_image=True), []))
    assert _timelines(content) == []
    assert NO_MATCHES_TEXT in _all_text(content)
