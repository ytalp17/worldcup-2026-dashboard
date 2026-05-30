from pathlib import Path

import pandas as pd
import pytest

from src.data.host_cities import HostCity, HostCityRepository

CSV_PATH = Path(__file__).parent.parent / "assets" / "data" / "fifa_2026_host_cities.csv"


def test_loads_all_sixteen_cities():
    cities = HostCityRepository(CSV_PATH).load()
    assert len(cities) == 16


def test_returns_hostcity_objects_with_correct_types():
    cities = HostCityRepository(CSV_PATH).load()
    city = cities[0]
    assert isinstance(city, HostCity)
    assert isinstance(city.city, str)
    assert isinstance(city.country, str)
    assert isinstance(city.stadium, str)
    assert isinstance(city.capacity, int)
    assert isinstance(city.lat, float)
    assert isinstance(city.lon, float)


def test_known_city_values():
    cities = HostCityRepository(CSV_PATH).load()
    azteca = next(c for c in cities if c.stadium == "Estadio Azteca")
    assert azteca.city == "Mexico City"
    assert azteca.country == "Mexico"
    assert azteca.capacity == 87523


def test_only_host_countries_present():
    cities = HostCityRepository(CSV_PATH).load()
    assert {c.country for c in cities} == {"USA", "Mexico", "Canada"}


def test_coordinates_within_valid_ranges():
    cities = HostCityRepository(CSV_PATH).load()
    for c in cities:
        assert -90.0 <= c.lat <= 90.0
        assert -180.0 <= c.lon <= 180.0


def test_hostcity_is_frozen():
    city = HostCity("X", "USA", "Y", 1, 0.0, 0.0)
    with pytest.raises(AttributeError):
        city.capacity = 2


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("City,Country,Stadium,Capacity,Latitude\nA,USA,S,1,10.0\n")
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()


def test_out_of_range_latitude_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "City,Country,Stadium,Capacity,Latitude,Longitude\n"
        "A,USA,S,1,200.0,10.0\n"
    )
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()


def test_non_numeric_capacity_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "City,Country,Stadium,Capacity,Latitude,Longitude\n"
        "A,USA,S,notanumber,10.0,10.0\n"
    )
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()


def test_blank_city_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "City,Country,Stadium,Capacity,Latitude,Longitude\n"
        ",USA,S,1,10.0,10.0\n"
    )
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()
