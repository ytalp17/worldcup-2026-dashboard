from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import dash_mantine_components as dmc
from dash import html

from src.data.live.reconcile import canonical_team, normalize
from src.data.team_continents import TEAM_CODE

# Normalized canonical team name -> FIFA 3-letter code, for compact strip labels.
_CODE_BY_NORM = {normalize(team): code for team, code in TEAM_CODE.items()}


def abbr(name: str) -> str:
    """FIFA 3-letter code for a (possibly live-API) team name, mapping aliases
    through canonical_team; the original name when no code is known."""
    return _CODE_BY_NORM.get(canonical_team(name), name)


def _score(m: dict) -> str:
    if m.get("home_score") is None:
        return "vs"
    return f"{m['home_score']} - {m['away_score']}"


def _local_time(iso_utc: str | None, user_tz: str | None) -> str | None:
    """Format a UTC ISO kickoff as 'HH:MM' in the user's zone, or None."""
    if not iso_utc or not user_tz:
        return None
    try:
        when = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return when.astimezone(ZoneInfo(user_tz)).strftime("%H:%M")
    except (ValueError, ZoneInfoNotFoundError):
        return None


def _badge(m: dict, user_tz: str | None = None):
    if m.get("is_live"):
        return dmc.Badge("LIVE", color="red", variant="filled", size="sm")
    if m.get("state") == "finished":
        return dmc.Badge("FT", color="gray", variant="light", size="sm")
    # Scheduled / upcoming: show the kickoff in the viewer's local time.
    local = _local_time(m.get("kickoff"), user_tz)
    if local:
        return dmc.Badge(local, color="gray", variant="light", size="sm")
    return dmc.Badge(m.get("state", ""), color="gray", variant="light", size="sm")


def strip_items(live: dict | None, user_tz: str | None = None) -> list:
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
                        [_badge(m, user_tz),
                         dmc.Text(f"{abbr(m['home'])} {_score(m)} {abbr(m['away'])}",
                                  size="sm", fw=600)],
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


# Base style for the fixed bottom-center overlay (see overlay_style()).
_OVERLAY_STYLE = {
    "position": "fixed",
    "bottom": "12px",
    "left": "50%",
    "transform": "translateX(-50%)",
    "zIndex": 1500,
    "pointerEvents": "auto",
}


def overlay_style(visible: bool = True) -> dict:
    """Style for the strip overlay; hidden (display:none) when not on the
    calendar/Time view. Base positioning is always preserved."""
    style = dict(_OVERLAY_STYLE)
    if not visible:
        style["display"] = "none"
    return style


def build_live_strip(live: dict | None = None):
    """Fixed-position bottom-center overlay; renders nothing when no matches.
    Inner Group has id 'live-strip' so a callback can refresh its children;
    the outer 'live-strip-overlay' is toggled to hide it off the calendar view."""
    return html.Div(
        dmc.Group(
            strip_items(live),
            id="live-strip",
            gap="sm",
            wrap="nowrap",
            style={"overflowX": "auto", "maxWidth": "98vw"},
        ),
        id="live-strip-overlay",
        style=overlay_style(visible=True),
    )
