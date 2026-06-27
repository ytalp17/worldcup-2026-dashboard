"""Tournament Knockout drawer: a Google-style bracket paged two stages at a time.

The drawer mirrors the other map-control drawers (frosted, right side). Its body
is rendered per carousel page by an app callback; each page (except the finals
page) is a vertical list of *ties* — one right-stage match centred between its two
feeder matches — so the bracket aligns and scrolls naturally.
"""
from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify

from src.components.team_carousel import display_name
from src.data.bracket import STAGE_PAGES, BracketMatch, stage_ties

_FROSTED = {"content": "filter-drawer-frosted ko-drawer-content",
            "header": "filter-drawer-frosted-header",
            "body": "ko-drawer-body"}


def format_ko_datetime(bm: BracketMatch, user_tz: str | None,
                       today: date) -> str:
    """Kickoff as 'Today, HH:MM' / 'Tomorrow, HH:MM' / 'Tue, 30 Jun, HH:MM',
    in the viewer's timezone when known (else the stored UTC clock)."""
    dt = bm.kickoff_utc
    if user_tz:
        try:
            dt = dt.astimezone(ZoneInfo(user_tz))
        except (ZoneInfoNotFoundError, ValueError):
            pass
    clock = dt.strftime("%H:%M")
    day = dt.date()
    if day == today:
        return f"Today, {clock}"
    if day == today + timedelta(days=1):
        return f"Tomorrow, {clock}"
    return f"{dt.strftime('%a')}, {dt.day} {dt.strftime('%b')}, {clock}"


def _slot_row(slot, asset_url):
    """One team line: flag + name + score when resolved, else a shield + TBD."""
    if slot.team:
        ident = dmc.Group(
            [dmc.Image(src=asset_url(f"flags/{slot.team}.png"),
                       w=22, h=15, fit="cover", className="ko-flag"),
             dmc.Text(display_name(slot.team), size="sm",
                      fw=700 if slot.winner else 500, className="ko-team")],
            gap=8, wrap="nowrap", align="center", className="ko-slot__ident")
    else:
        ident = dmc.Group(
            [DashIconify(icon="tabler:shield-filled", width=16,
                         className="ko-shield"),
             dmc.Text("TBD", size="sm", c="dimmed", className="ko-team")],
            gap=8, wrap="nowrap", align="center", className="ko-slot__ident")
    score = dmc.Text("" if slot.score is None else str(slot.score),
                     size="sm", fw=700, className="ko-score")
    cls = "ko-slot" + (" ko-slot--win" if slot.winner else "")
    return dmc.Group([ident, score], justify="space-between", wrap="nowrap",
                     align="center", className=cls)


def match_card(bm: BracketMatch, asset_url, user_tz, today) -> dmc.Box:
    """A single bracket match card: date/time header over the two team rows."""
    cls = "ko-card ko-card--done" if bm.finished else "ko-card"
    children = [dmc.Text(format_ko_datetime(bm, user_tz, today), size="xs",
                         c="dimmed", className="ko-card__time"),
                _slot_row(bm.home, asset_url),
                _slot_row(bm.away, asset_url)]
    if bm.venue:
        children.append(dmc.Group(
            [DashIconify(icon="tabler:map-pin", width=12, className="ko-pin"),
             dmc.Text(bm.venue, size="xs", c="dimmed", className="ko-venue__text")],
            gap=4, wrap="nowrap", align="center", className="ko-venue"))
    return dmc.Box(children, className=cls)


def _tie_row(winner_match, feeders, asset_url, user_tz, today) -> dmc.Box:
    feeders_col = dmc.Box(
        [match_card(f, asset_url, user_tz, today) for f in feeders],
        className="ko-feeders")
    winner_col = dmc.Box(
        match_card(winner_match, asset_url, user_tz, today), className="ko-winner")
    return dmc.Box([feeders_col, dmc.Box(className="ko-connector"), winner_col],
                   className="ko-tie")


def _stage_headers(left, right) -> dmc.Group:
    return dmc.Group(
        [dmc.Text(left, fw=700, size="sm", className="ko-stage-headers__left"),
         dmc.Text(right, fw=700, size="sm", className="ko-stage-headers__right")],
        justify="space-between", wrap="nowrap", className="ko-stage-headers")


def _final_col(bm, label, asset_url, user_tz, today, extra="") -> dmc.Box:
    return dmc.Box(
        [dmc.Text(label, fw=700, size="sm", className="ko-final-label"),
         match_card(bm, asset_url, user_tz, today)],
        className=f"ko-final {extra}".strip())


def render_page(bracket, page: int, asset_url, user_tz, today) -> dmc.Box:
    """The bracket body for one carousel page (a pair of stages)."""
    left, right = STAGE_PAGES[page]
    if page == len(STAGE_PAGES) - 1:
        # Finals page: the Final and the 3rd-Place final, side by side.
        cols = []
        if bracket.get("Final"):
            cols.append(_final_col(bracket["Final"][0], "Final",
                                   asset_url, user_tz, today))
        if bracket.get("Bronze Final"):
            cols.append(_final_col(bracket["Bronze Final"][0], "3rd Place",
                                   asset_url, user_tz, today, "ko-final--bronze"))
        return dmc.Box(cols, className="ko-page ko-page--finals")

    rows = [_tie_row(wm, feeders, asset_url, user_tz, today)
            for wm, feeders in stage_ties(bracket, left, right)]
    return dmc.Box([_stage_headers(left, right),
                    dmc.Box(rows, className="ko-ties")], className="ko-page")


def page_dots(active: int):
    """Carousel page indicator dots (one per stage-pair)."""
    return [dmc.Box(className="ko-dot" + (" ko-dot--active" if i == active else ""))
            for i in range(len(STAGE_PAGES))]


def build_knockout_drawer() -> dmc.Drawer:
    """Right-side frosted drawer holding the paged knockout bracket."""
    controls = dmc.Group(
        [dmc.ActionIcon(DashIconify(icon="tabler:chevron-left", width=18),
                        id="knockout-prev", variant="subtle", radius="xl",
                        size="lg"),
         dmc.Group(page_dots(0), id="knockout-dots", gap=6, justify="center",
                   wrap="nowrap"),
         dmc.ActionIcon(DashIconify(icon="tabler:chevron-right", width=18),
                        id="knockout-next", variant="subtle", radius="xl",
                        size="lg")],
        justify="space-between", align="center", wrap="nowrap",
        className="ko-controls")

    body = dmc.Box(id="knockout-body", className="ko-body")

    return dmc.Drawer(
        id="knockout-drawer",
        title="Tournament Knockout",
        position="right",
        size=540,  # narrower than the other drawers; cards are compact
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        classNames=_FROSTED,
        children=[dmc.Stack([controls, body], gap="sm", className="ko-stack"),
                  dcc.Store(id="knockout-page", data=0)],
    )
