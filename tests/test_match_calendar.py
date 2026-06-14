from datetime import date
from pathlib import Path

from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository
from src.data.venues import VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
TODAY = date(2026, 5, 30)


def _calendar(today=TODAY):
    venues = VenueRepository(DATA / "venues.csv", IMAGE_DIR).load()
    stadium_to_city = {v.stadium_name: v.city for v in venues}
    matches = MatchRepository(DATA / "matches.csv").load()
    return MatchCalendar(matches, stadium_to_city, today=today)


def test_start_is_earliest_match_day_and_end_is_final_day():
    # start is now the opening match day (June 11), not today (May 30).
    cal = _calendar()
    assert cal.start == date(2026, 6, 11)
    assert cal.end == date(2026, 7, 19)


def test_match_dates_cover_all_match_days():
    cal = _calendar()
    md = cal.match_dates
    assert len(md) == 34
    assert date(2026, 6, 11) in md  # opening day
    assert TODAY not in md  # today has no match


def test_active_cities_for_opening_day():
    cal = _calendar()
    assert cal.active_cities(date(2026, 6, 11)) == {"Mexico City", "Guadalajara"}


def test_active_cities_empty_for_non_match_day():
    cal = _calendar()
    assert cal.active_cities(TODAY) == set()


def test_active_cities_user_tz_shifts_match_to_next_day():
    cal = _calendar()
    # Opening matches are Jun 11 in venue time; from Tokyo they fall on Jun 12.
    assert "Mexico City" not in cal.active_cities(date(2026, 6, 11), "Asia/Tokyo")
    assert "Mexico City" in cal.active_cities(date(2026, 6, 12), "Asia/Tokyo")


def test_active_cities_user_tz_none_uses_venue_dates():
    cal = _calendar()
    assert cal.active_cities(date(2026, 6, 11), None) == {"Mexico City", "Guadalajara"}


def test_start_is_earliest_match_date_not_today():
    from datetime import date, time, datetime
    from src.data.matches import Match
    from src.data.match_calendar import MatchCalendar
    def m(num, d, stadium="Dallas Stadium"):
        return Match(number=num, home="A", away="B", group="G", stage="Group Stage",
                     stadium=stadium, date=d, local_time=time(12, 0),
                     kickoff_utc=datetime(d.year, d.month, d.day, 18, 0))
    matches = [m(1, date(2026, 6, 11)), m(2, date(2026, 6, 20))]
    cal = MatchCalendar(matches, {"Dallas Stadium": "Dallas"}, today=date(2026, 6, 13))
    assert cal.start == date(2026, 6, 11)
    assert cal.end == date(2026, 6, 20)
    assert cal.default_day == date(2026, 6, 13)


def test_default_day_clamped_into_range():
    from datetime import date, time, datetime
    from src.data.matches import Match
    from src.data.match_calendar import MatchCalendar
    def m(num, d):
        return Match(number=num, home="A", away="B", group="G", stage="Group Stage",
                     stadium="Dallas Stadium", date=d, local_time=time(12, 0),
                     kickoff_utc=datetime(d.year, d.month, d.day, 18, 0))
    matches = [m(1, date(2026, 6, 11)), m(2, date(2026, 6, 20))]
    cal = MatchCalendar(matches, {"Dallas Stadium": "Dallas"}, today=date(2026, 6, 1))
    assert cal.default_day == date(2026, 6, 11)
