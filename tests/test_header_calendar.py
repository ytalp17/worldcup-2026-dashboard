from datetime import date

import dash_mantine_components as dmc

from src.components.header_calendar import CALENDAR_ID, build_match_calendar


class _FakeCalendar:
    # start = earliest match date (opening day), not today
    start = date(2026, 6, 11)
    end = date(2026, 7, 19)
    # default_day = today clamped into [start, end]
    default_day = date(2026, 6, 13)


def test_minicalendar_has_range_value_and_window():
    mc = build_match_calendar(_FakeCalendar())
    assert isinstance(mc, dmc.MiniCalendar)
    assert mc.id == CALENDAR_ID
    # value and defaultDate open the calendar on today (clamped)
    assert mc.value == "2026-06-13"
    assert mc.defaultDate == "2026-06-13"
    # minDate goes back to opening day so users can scroll to past matches
    assert mc.minDate == "2026-06-11"
    # maxDate is padded one day past the final venue day so user-local edge
    # dates (late-night kickoffs that roll to the next day) stay selectable.
    assert mc.maxDate == "2026-07-20"
    assert mc.numberOfDays == 10
