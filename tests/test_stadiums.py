from pathlib import Path

import pytest

from src.data.stadiums import Stadium, StadiumRepository

CSV_PATH = Path(__file__).parent.parent / "assets" / "data" / "fifa_wc2026_stadiums.csv"


def test_loads_all_sixteen_stadiums():
    stadiums = StadiumRepository(CSV_PATH).load()
    assert len(stadiums) == 16


def test_returns_stadium_objects_with_correct_types():
    stadiums = StadiumRepository(CSV_PATH).load()
    s = stadiums[0]
    assert isinstance(s, Stadium)
    assert isinstance(s.name, str)
    assert isinstance(s.country, str)
    assert isinstance(s.location, str)
    assert isinstance(s.capacity, int)
    assert isinstance(s.opened, int)
    assert isinstance(s.info, str)
    assert isinstance(s.image_filename, str)


def test_known_stadium_values():
    stadiums = StadiumRepository(CSV_PATH).load()
    dallas = next(s for s in stadiums if s.name == "Dallas Stadium")
    assert dallas.country == "USA"
    assert dallas.capacity == 94000
    assert dallas.opened == 2009
    assert dallas.image_filename == "Dallas_Stadium.jpg"
    assert "Dallas Stadium" in dallas.info


def test_stadium_is_frozen():
    s = Stadium("X Stadium", "USA", "X, USA", 1, 2000, "info", "X.jpg")
    with pytest.raises(AttributeError):
        s.capacity = 2


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Stadium,Country,Location,Capacity,Opened,Info\nA,USA,X,1,2000,i\n")
    with pytest.raises(ValueError):
        StadiumRepository(bad).load()


def test_non_numeric_capacity_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Stadium,Country,Location,Capacity,Opened,Info,Image_Filename,Image_URL\n"
        "A,USA,X,notanumber,2000,i,A.jpg,http://x\n"
    )
    with pytest.raises(ValueError):
        StadiumRepository(bad).load()


def test_blank_name_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Stadium,Country,Location,Capacity,Opened,Info,Image_Filename,Image_URL\n"
        ",USA,X,1,2000,i,A.jpg,http://x\n"
    )
    with pytest.raises(ValueError):
        StadiumRepository(bad).load()
