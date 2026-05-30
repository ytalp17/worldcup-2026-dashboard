from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.venues import Venue

PLACEHOLDER_TEXT = "Photo unavailable"
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


def stadium_detail(venue: Venue):
    """Drawer body for a venue: photo, location, key stats, and info blurb."""
    return dmc.Stack(
        [
            _image_block(venue),
            dmc.Text(venue.location, size="sm", c="dimmed"),
            dmc.Group(
                [
                    dmc.Badge(
                        f"Capacity {venue.capacity:,}",
                        variant="light",
                        color="blue",
                    ),
                    dmc.Badge(
                        f"Opened {venue.opened}",
                        variant="light",
                        color="teal",
                    ),
                ],
                gap="sm",
            ),
            dmc.Group(
                [
                    DashIconify(icon="tabler:clock-hour-4", width=16),
                    dmc.Text(_timezone_text(venue), size="sm", c="dimmed"),
                ],
                gap="xs",
                align="center",
                wrap="nowrap",
            ),
            dmc.ScrollArea(
                dmc.Text(venue.info, size="sm"),
                h=240,
                type="auto",
                offsetScrollbars=True,
            ),
        ],
        gap="md",
    )
