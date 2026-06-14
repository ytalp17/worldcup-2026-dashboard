from pathlib import Path

import pandas as pd
import pytest

from src.data.venues import Venue, VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
VENUES_CSV = DATA / "venues.csv"
IMAGE_DIR = DATA.parent / "stadiums"


def _venues(image_dir=IMAGE_DIR):
    return VenueRepository(VENUES_CSV, image_dir).load()


def test_loads_sixteen_venues():
    venues = _venues()
    assert len(venues) == 16
    assert all(isinstance(v, Venue) for v in venues)


def test_dallas_fields_joined_correctly():
    dallas = next(v for v in _venues() if v.city == "Dallas")
    assert dallas.official_name == "AT&T Stadium"
    assert dallas.stadium_name == "Dallas Stadium"
    assert dallas.capacity == 94000
    assert dallas.opened == 2009
    assert dallas.lat == pytest.approx(32.7473)
    assert dallas.lon == pytest.approx(-97.0945)
    assert dallas.altitude_m == 183
    assert dallas.timezone == "America/Chicago"
    assert dallas.tz_label == "Central Time"
    assert dallas.airport_code == "DAL"
    assert dallas.region_cluster == "Central"


def test_every_venue_has_timezone_and_altitude():
    venues = _venues()
    assert all(v.timezone and v.tz_label for v in venues)
    assert all(isinstance(v.altitude_m, int) for v in venues)


def test_has_image_reflects_file_presence(tmp_path):
    (tmp_path / "Dallas_Stadium.jpg").write_bytes(b"jpegbytes")
    by_city = {v.city: v for v in _venues(tmp_path)}
    assert by_city["Dallas"].has_image is True
    assert by_city["Monterrey"].has_image is False


def test_image_src_under_stadiums_assets():
    dallas = next(v for v in _venues() if v.city == "Dallas")
    assert dallas.image_src == "/assets/stadiums/Dallas_Stadium.jpg"


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("city,country\nDallas,USA\n")
    with pytest.raises(ValueError):
        VenueRepository(bad, tmp_path).load()


def test_out_of_range_latitude_raises(tmp_path):
    src = pd.read_csv(VENUES_CSV)
    src.loc[0, "latitude"] = 200.0
    bad = tmp_path / "bad.csv"
    src.to_csv(bad, index=False)
    with pytest.raises(ValueError):
        VenueRepository(bad, tmp_path).load()
