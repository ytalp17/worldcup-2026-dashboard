from __future__ import annotations

from collections.abc import Sequence

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.kickoff import KickoffView, kickoff_view, venue_offset_tag
from src.data.matches import Match, is_placeholder
from src.data.venues import Venue
from src.components.map_view import live_match_for_venue

PLACEHOLDER_TEXT = "Photo unavailable"
NO_MATCHES_TEXT = "No matches scheduled"
IMAGE_HEIGHT = 200


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


def _kickoff_line(kv: KickoffView) -> dmc.Group:
    if kv.same_clock:
        return dmc.Group(
            [dmc.Text(f"{kv.venue_time} local", size="xs", c="dimmed")],
            gap=4,
            align="center",
            wrap="nowrap",
        )
    tag = venue_offset_tag(kv.venue_day_offset)
    local_text = f"{kv.venue_time} local {tag}".strip()
    return dmc.Group(
        [
            DashIconify(icon="tabler:world", width=14),
            dmc.Text(f"{kv.user_time} your time", size="xs", fw=500),
            dmc.Text("·", size="xs", c="dimmed"),
            dmc.Text(local_text, size="xs", c="dimmed"),
        ],
        gap=4,
        align="center",
        wrap="nowrap",
    )


def _match_item(match: Match, user_tz: str | None) -> dmc.TimelineItem:
    kv = kickoff_view(match, user_tz)
    day = kv.user_date or match.date  # user-local date is the anchor when known
    title = f"{day.strftime('%b')} {day.day} · {_match_label(match)}"
    return dmc.TimelineItem(
        title=title,
        bullet=DashIconify(icon="tabler:ball-football", width=12),
        children=[
            dmc.Text(
                [_team_span(match.home), " vs ", _team_span(match.away)],
                size="sm",
            ),
            _kickoff_line(kv),
        ],
    )


def _matches_section(matches: Sequence[Match], user_tz: str | None):
    header = dmc.Group(
        [
            dmc.Text("Matches", fw=600),
            dmc.Badge(str(len(matches)), variant="light", color="grape", size="sm"),
        ],
        gap="xs",
        align="center",
    )
    note_text = (
        f"Times in {user_tz}, with local time alongside"
        if user_tz
        else "Times in local time"
    )
    note = dmc.Text(note_text, size="xs", c="dimmed")
    if not matches:
        body = dmc.Text(NO_MATCHES_TEXT, size="sm", c="dimmed")
    else:
        body = dmc.Timeline(
            [_match_item(m, user_tz) for m in matches],
            active=len(matches),
            bulletSize=20,
            lineWidth=2,
        )
    return dmc.Stack([header, note, body], gap="sm")


def _live_section(match: dict):
    h, a = match.get("home_score"), match.get("away_score")
    score = f"{h} - {a}" if h is not None else "vs"
    state = (match.get("state") or "").upper()
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Badge("LIVE", color="red", variant="filled"),
                        dmc.Text(state, size="xs", c="dimmed"),
                    ],
                    gap="xs",
                    align="center",
                ),
                dmc.Text(f"{match['home']}  {score}  {match['away']}", fw=600),
                dmc.Button(
                    "Match details",
                    id={"type": "open-live-modal", "index": match["match_id"]},
                    n_clicks=0,
                    size="xs",
                    variant="light",
                    color="red",
                ),
            ],
            gap="xs",
        ),
        withBorder=True,
        p="sm",
        radius="md",
    )


def stadium_detail(venue: Venue, matches: Sequence[Match] = (), user_tz: str | None = None,
                   live: dict | None = None):
    """Drawer body: photo, location, key stats, info, the live match (if any at
    this venue, with a button to open the detail modal), then the schedule."""
    children = [
        _image_block(venue),
        dmc.Text(venue.location, size="sm", c="dimmed"),
        dmc.Group(_stat_badges(venue), gap="sm"),
        dmc.Text(venue.info, size="sm"),
    ]
    match = live_match_for_venue(venue.stadium_name, live)
    if match:
        children.append(dmc.Divider())
        children.append(_live_section(match))
    children.append(dmc.Divider())
    children.append(_matches_section(matches, user_tz))
    return dmc.Stack(children, gap="md")
