from __future__ import annotations

from datetime import timedelta

import dash_mantine_components as dmc

from src.data.match_calendar import MatchCalendar

CALENDAR_ID = "match-calendar"


CALENDAR_DAYS = 10


def build_match_calendar(calendar: MatchCalendar) -> dmc.MiniCalendar:
    """Compact header calendar spanning the opening day -> the final day. Opens on
    today (clamped); users can scroll back for past days."""
    return dmc.MiniCalendar(
        id=CALENDAR_ID,
        value=calendar.default_day.isoformat(),
        defaultDate=calendar.default_day.isoformat(),
        minDate=calendar.start.isoformat(),
        maxDate=(calendar.end + timedelta(days=1)).isoformat(),
        numberOfDays=CALENDAR_DAYS,
        persistence=True,
    )
