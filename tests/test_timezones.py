import pytest

from src.data.timezones import CITY_TIMEZONES, timezone_for


def test_known_city_timezones():
    assert timezone_for("Dallas") == ("America/Chicago", "Central Time")
    assert timezone_for("Los Angeles") == ("America/Los_Angeles", "Pacific Time")
    assert timezone_for("New York/New Jersey") == ("America/New_York", "Eastern Time")
    assert timezone_for("Mexico City") == ("America/Mexico_City", "Central Time")


def test_unknown_city_raises():
    with pytest.raises(ValueError):
        timezone_for("Atlantis")


def test_map_has_all_sixteen_host_cities():
    assert len(CITY_TIMEZONES) == 16


def test_all_zones_are_valid_iana():
    from zoneinfo import ZoneInfo

    for iana, _label in CITY_TIMEZONES.values():
        ZoneInfo(iana)  # raises if not a real zone
