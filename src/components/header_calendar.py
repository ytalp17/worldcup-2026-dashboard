from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc

from src.data.match_calendar import MatchCalendar

CALENDAR_ID = "match-calendar"
SELECTED_DATE_ID = "calendar-selected-date"


CALENDAR_DAYS = 10


def format_selected_day(value: str | None) -> str:
    """Human-readable label for the selected calendar day, e.g.
    'Thursday, 25 June 2026'. Tolerates ISO datetimes (takes the date part)
    and returns '' for blank/unparseable input."""
    if not value:
        return ""
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return ""
    return f"{d:%A}, {d.day} {d:%B %Y}"


def build_match_calendar(calendar: MatchCalendar) -> dmc.Stack:
    """Compact header calendar spanning the opening day -> the final day, with
    the selected day's date spelled out just beneath it. Opens on today
    (clamped); users can scroll back for past days."""
    mini = dmc.MiniCalendar(
        id=CALENDAR_ID,
        value=calendar.default_day.isoformat(),
        defaultDate=calendar.default_day.isoformat(),
        minDate=calendar.start.isoformat(),
        maxDate=(calendar.end + timedelta(days=1)).isoformat(),
        numberOfDays=CALENDAR_DAYS,
        persistence=True,
    )
    label = dmc.Text(
        format_selected_day(calendar.default_day.isoformat()),
        id=SELECTED_DATE_ID,
        size="xs",
        c="dimmed",
        ta="center",
    )
    return dmc.Stack([mini, label], gap=2, align="center")
