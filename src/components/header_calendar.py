from __future__ import annotations

import dash_mantine_components as dmc

from src.data.match_calendar import MatchCalendar

CALENDAR_ID = "match-calendar"


def build_match_calendar(calendar: MatchCalendar) -> dmc.MiniCalendar:
    """Compact header calendar spanning today → the final day.

    Match-days blink via the ``wcMatchDay`` client-side function (registered in
    assets/dmc_functions.js, fed by ``window.WC_MATCH_DATES``). The selected
    ``value`` drives the map highlight callback in app.py.
    """
    return dmc.MiniCalendar(
        id=CALENDAR_ID,
        value=calendar.start.isoformat(),
        defaultDate=calendar.start.isoformat(),
        minDate=calendar.start.isoformat(),
        maxDate=calendar.end.isoformat(),
        numberOfDays=5,
        getDayProps={"function": "wcMatchDay"},
        persistence=True,
    )
