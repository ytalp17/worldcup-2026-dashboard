from pathlib import Path

import pytest

from src.data.host_cities import HostCity, HostCityRepository
from src.data.stadiums import Stadium, StadiumRepository
from src.data.venues import Venue, build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
CITIES_CSV = DATA / "fifa_2026_host_cities.csv"
STADIUMS_CSV = DATA / "fifa_wc2026_stadiums.csv"
IMAGE_DIR = DATA.parent / "stadiums"


def _real_inputs():
    cities = HostCityRepository(CITIES_CSV).load()
    stadiums = StadiumRepository(STADIUMS_CSV).load()
    return cities, stadiums


def test_all_sixteen_cities_join():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    assert len(venues) == 16
    assert all(isinstance(v, Venue) for v in venues)


def test_venue_altitude_from_mapping():
    cities, stadiums = _real_inputs()
    altitudes = {"Mexico City": 2240, "Dallas": 183}
    venues = build_venues(cities, stadiums, IMAGE_DIR, altitudes)
    by_city = {v.city: v for v in venues}
    assert by_city["Mexico City"].altitude_m == 2240
    assert by_city["Dallas"].altitude_m == 183
    # Cities absent from the mapping get None (no altitude).
    assert by_city["Toronto"].altitude_m is None


def test_venue_altitude_defaults_none_without_mapping():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    assert all(v.altitude_m is None for v in venues)


def test_every_venue_carries_a_timezone():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    assert all(v.timezone and v.tz_label for v in venues)
    dallas = next(v for v in venues if v.city == "Dallas")
    assert dallas.timezone == "America/Chicago"
    assert dallas.tz_label == "Central Time"


def test_venue_carries_generic_stadium_name_for_match_join():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    dallas = next(v for v in venues if v.city == "Dallas")
    assert dallas.stadium_name == "Dallas Stadium"


def test_venue_combines_coords_and_detail():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    dallas = next(v for v in venues if v.city == "Dallas")
    # Coordinates + official name come from the host-cities source.
    assert dallas.official_name == "AT&T Stadium"
    assert dallas.lat == pytest.approx(32.7473)
    assert dallas.lon == pytest.approx(-97.0945)
    # Capacity, opened, info, image come from the stadium-detail source.
    assert dallas.capacity == 94000
    assert dallas.opened == 2009
    assert dallas.image_filename == "Dallas_Stadium.jpg"
    assert "Dallas Stadium" in dallas.info


def test_has_image_reflects_file_presence(tmp_path):
    cities, stadiums = _real_inputs()
    # Only Dallas image exists in this temp dir.
    (tmp_path / "Dallas_Stadium.jpg").write_bytes(b"jpegbytes")
    venues = build_venues(cities, stadiums, tmp_path)
    by_city = {v.city: v for v in venues}
    assert by_city["Dallas"].has_image is True
    assert by_city["Monterrey"].has_image is False


def test_image_path_is_under_stadiums_assets():
    cities, stadiums = _real_inputs()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    dallas = next(v for v in venues if v.city == "Dallas")
    assert dallas.image_src == "/assets/stadiums/Dallas_Stadium.jpg"


def test_unmatched_city_raises(tmp_path):
    cities = [HostCity("Nowhere", "USA", "Ghost Stadium", 1, 10.0, 10.0)]
    stadiums = [Stadium("Dallas Stadium", "USA", "Arlington", 1, 2009, "i", "D.jpg")]
    with pytest.raises(ValueError):
        build_venues(cities, stadiums, tmp_path)


def test_ambiguous_match_raises(tmp_path):
    cities = [HostCity("San", "USA", "S", 1, 10.0, 10.0)]
    stadiums = [
        Stadium("San Diego Stadium", "USA", "San Diego", 1, 2000, "i", "a.jpg"),
        Stadium("San Antonio Stadium", "USA", "San Antonio", 1, 2000, "i", "b.jpg"),
    ]
    with pytest.raises(ValueError):
        build_venues(cities, stadiums, tmp_path)
