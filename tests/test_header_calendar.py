from datetime import date

import dash_mantine_components as dmc

from src.components.header_calendar import (
    CALENDAR_ID,
    SELECTED_DATE_ID,
    build_match_calendar,
    format_selected_day,
)


class _FakeCalendar:
    # start = earliest match date (opening day), not today
    start = date(2026, 6, 11)
    end = date(2026, 7, 19)
    # default_day = today clamped into [start, end]
    default_day = date(2026, 6, 13)


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


def _minicalendar(root):
    return next(n for n in _walk(root) if isinstance(n, dmc.MiniCalendar))


def test_minicalendar_has_range_value_and_window():
    root = build_match_calendar(_FakeCalendar())
    mc = _minicalendar(root)
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


def test_selected_date_label_present_and_seeded_with_default_day():
    root = build_match_calendar(_FakeCalendar())
    labels = [n for n in _walk(root)
              if isinstance(n, dmc.Text) and getattr(n, "id", None) == SELECTED_DATE_ID]
    assert len(labels) == 1
    assert labels[0].children == "Saturday, 13 June 2026"


def test_format_selected_day_human_readable():
    assert format_selected_day("2026-06-25") == "Thursday, 25 June 2026"


def test_format_selected_day_tolerates_datetime_and_blank():
    assert format_selected_day("2026-07-19T21:00:00") == "Sunday, 19 July 2026"
    assert format_selected_day("") == ""
    assert format_selected_day(None) == ""
    assert format_selected_day("not-a-date") == ""
