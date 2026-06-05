from datetime import date, datetime, time

from src.data.kickoff import KickoffView, kickoff_view, venue_offset_tag
from src.data.matches import Match


def _match(local="13:00", utc="2026-06-11T19:00:00+00:00", day=11):
    return Match(
        number=1, home="Mexico", away="South Africa", group="Group A",
        stage="Group Stage", stadium="Mexico City Stadium",
        date=date(2026, 6, day),
        local_time=time.fromisoformat(local),
        kickoff_utc=datetime.fromisoformat(utc),
    )


def test_unknown_tz_falls_back_to_venue_only():
    kv = kickoff_view(_match(), None)
    assert kv == KickoffView(
        user_time=None, user_date=None, venue_time="13:00",
        venue_day_offset=0, same_clock=True,
    )


def test_bad_tz_string_falls_back():
    kv = kickoff_view(_match(), "Not/AZone")
    assert kv.user_time is None and kv.same_clock is True


def test_same_zone_collapses_to_single_time():
    kv = kickoff_view(_match(), "America/Mexico_City")
    assert kv.user_time == "13:00"
    assert kv.venue_time == "13:00"
    assert kv.venue_day_offset == 0
    assert kv.same_clock is True


def test_eastward_viewer_crosses_to_next_day():
    # 13:00 Mexico City (19:00Z) seen from Tokyo (UTC+9) -> 04:00 next day.
    kv = kickoff_view(_match(), "Asia/Tokyo")
    assert kv.user_time == "04:00"
    assert kv.user_date == date(2026, 6, 12)
    assert kv.venue_day_offset == -1
    assert kv.same_clock is False


def test_venue_offset_tag_formatting():
    assert venue_offset_tag(0) == ""
    assert venue_offset_tag(-1) == "(-1d)"
    assert venue_offset_tag(1) == "(+1d)"
    assert venue_offset_tag(2) == "(+2d)"
