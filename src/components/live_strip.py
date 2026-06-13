from __future__ import annotations

import dash_mantine_components as dmc
from dash import html


def _score(m: dict) -> str:
    if m.get("home_score") is None:
        return "vs"
    return f"{m['home_score']} - {m['away_score']}"


def _badge(m: dict):
    if m.get("is_live"):
        return dmc.Badge("LIVE", color="red", variant="filled", size="sm")
    return dmc.Badge(m.get("state", ""), color="gray", variant="light", size="sm")


def strip_items(live: dict | None) -> list:
    """One clickable item per match; the pattern-matching id carries match_id so
    the modal callback can open from a click. Empty list when no matches."""
    items = []
    for m in (live or {}).get("matches", []):
        items.append(
            html.Div(
                id={"type": "live-strip-item", "index": m["match_id"]},
                n_clicks=0,
                style={"cursor": "pointer"},
                children=dmc.Paper(
                    dmc.Group(
                        [_badge(m),
                         dmc.Text(f"{m['home']} {_score(m)} {m['away']}", size="sm",
                                  fw=600)],
                        gap="xs",
                        wrap="nowrap",
                    ),
                    withBorder=True,
                    p="xs",
                    radius="md",
                    shadow="sm",
                ),
            )
        )
    return items


def build_live_strip(live: dict | None = None):
    """Fixed-position bottom-center overlay; renders nothing when no matches.
    Inner Group has id 'live-strip' so a callback can refresh its children."""
    return html.Div(
        dmc.Group(
            strip_items(live),
            id="live-strip",
            gap="sm",
            wrap="nowrap",
            style={"overflowX": "auto", "maxWidth": "92vw"},
        ),
        style={
            "position": "fixed",
            "bottom": "12px",
            "left": "50%",
            "transform": "translateX(-50%)",
            "zIndex": 1500,
            "pointerEvents": "auto",
        },
    )
