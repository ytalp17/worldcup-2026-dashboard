from datetime import date
from pathlib import Path

from src.data.host_cities import HostCityRepository
from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
TODAY = date(2026, 5, 30)


def _calendar(today=TODAY):
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    stadium_to_city = {v.stadium_name: v.city for v in venues}
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    return MatchCalendar(matches, stadium_to_city, today=today)


def test_start_is_today_and_end_is_final_day():
    cal = _calendar()
    assert cal.start == TODAY
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
