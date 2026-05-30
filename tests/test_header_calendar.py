from datetime import date

import dash_mantine_components as dmc

from src.components.header_calendar import CALENDAR_ID, build_match_calendar


class _FakeCalendar:
    start = date(2026, 5, 30)
    end = date(2026, 7, 19)


def test_minicalendar_has_range_value_and_window():
    mc = build_match_calendar(_FakeCalendar())
    assert isinstance(mc, dmc.MiniCalendar)
    assert mc.id == CALENDAR_ID
    # Default selected date is today; window opens there too.
    assert mc.value == "2026-05-30"
    assert mc.minDate == "2026-05-30"
    assert mc.maxDate == "2026-07-19"
    # Shows a 10-day window.
    assert mc.numberOfDays == 10
