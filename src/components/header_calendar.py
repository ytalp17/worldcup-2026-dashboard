from __future__ import annotations

import dash_mantine_components as dmc

from src.data.match_calendar import MatchCalendar

CALENDAR_ID = "match-calendar"


CALENDAR_DAYS = 10


def build_match_calendar(calendar: MatchCalendar) -> dmc.MiniCalendar:
    """Compact header calendar spanning today → the final day. Selecting a date
    drives the map highlight callback in app.py (active stadiums pulse)."""
    return dmc.MiniCalendar(
        id=CALENDAR_ID,
        value=calendar.start.isoformat(),
        defaultDate=calendar.start.isoformat(),
        minDate=calendar.start.isoformat(),
        maxDate=calendar.end.isoformat(),
        numberOfDays=CALENDAR_DAYS,
        persistence=True,
    )
