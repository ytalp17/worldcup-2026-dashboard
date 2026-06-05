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
    assert mc.value == "2026-05-30"
    assert mc.minDate == "2026-05-30"
    # maxDate is padded one day past the final venue day so user-local edge
    # dates (late-night kickoffs that roll to the next day) stay selectable.
    assert mc.maxDate == "2026-07-20"
    assert mc.numberOfDays == 10
