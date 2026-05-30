from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.matches import Match, is_placeholder
from src.data.venues import Venue

PLACEHOLDER_TEXT = "Photo unavailable"
NO_MATCHES_TEXT = "No matches scheduled"
IMAGE_HEIGHT = 200


def _timezone_text(venue: Venue) -> str:
    """e.g. 'Central Time · UTC-05:00 · America/Chicago'."""
    offset = datetime.now(ZoneInfo(venue.timezone)).strftime("%z")
    pretty = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
    return f"{venue.tz_label} · {pretty} · {venue.timezone}"


def _image_block(venue: Venue):
    if venue.has_image:
        return dmc.Image(
            src=venue.image_src,
            alt=venue.official_name,
            h=IMAGE_HEIGHT,
            fit="cover",
            radius="md",
        )
    return dmc.Paper(
        dmc.Center(
            dmc.Stack(
                [
                    DashIconify(icon="tabler:photo-off", width=36),
                    dmc.Text(PLACEHOLDER_TEXT, size="sm", c="dimmed"),
                ],
                align="center",
                gap="xs",
            ),
            h=IMAGE_HEIGHT,
        ),
        withBorder=True,
        radius="md",
        bg="var(--mantine-color-default-hover)",
    )


def _stat_badges(venue: Venue):
    badges = [
        dmc.Badge(f"Capacity {venue.capacity:,}", variant="light", color="blue"),
        dmc.Badge(f"Opened {venue.opened}", variant="light", color="teal"),
    ]
    if venue.altitude_m is not None:
        badges.append(
            dmc.Badge(f"Altitude {venue.altitude_m:,} m", variant="light", color="orange")
        )
    return badges


def _match_label(match: Match) -> str:
    """Group name for group-stage matches, otherwise the stage name."""
    return match.group or match.stage


def _team_span(name: str):
    """Render a team name; not-yet-decided slots are italic + dimmed."""
    if is_placeholder(name):
        return dmc.Text(name, span=True, fs="italic", c="dimmed")
    return dmc.Text(name, span=True, fw=500)


def _match_item(match: Match) -> dmc.TimelineItem:
    title = f"{match.date.strftime('%b')} {match.date.day} · {_match_label(match)}"
    return dmc.TimelineItem(
        title=title,
        bullet=DashIconify(icon="tabler:ball-football", width=12),
        children=[
            dmc.Text(
                [_team_span(match.home), " vs ", _team_span(match.away)],
                size="sm",
            )
        ],
    )


def _matches_section(matches: Sequence[Match]):
    header = dmc.Group(
        [
            dmc.Text("Matches", fw=600),
            dmc.Badge(str(len(matches)), variant="light", color="grape", size="sm"),
        ],
        gap="xs",
        align="center",
    )
    if not matches:
        body = dmc.Text(NO_MATCHES_TEXT, size="sm", c="dimmed")
    else:
        body = dmc.Timeline(
            [_match_item(m) for m in matches],
            active=len(matches),
            bulletSize=20,
            lineWidth=2,
        )
    return dmc.Stack([header, body], gap="sm")


def stadium_detail(venue: Venue, matches: Sequence[Match] = ()):
    """Drawer body: photo, location, key stats, timezone, info, and the
    schedule of matches at this stadium."""
    return dmc.Stack(
        [
            _image_block(venue),
            dmc.Text(venue.location, size="sm", c="dimmed"),
            dmc.Group(_stat_badges(venue), gap="sm"),
            dmc.Group(
                [
                    DashIconify(icon="tabler:clock-hour-4", width=16),
                    dmc.Text(_timezone_text(venue), size="sm", c="dimmed"),
                ],
                gap="xs",
                align="center",
                wrap="nowrap",
            ),
            dmc.Text(venue.info, size="sm"),
            dmc.Divider(),
            _matches_section(matches),
        ],
        gap="md",
    )
