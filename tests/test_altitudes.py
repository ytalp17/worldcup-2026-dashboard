from pathlib import Path

import pytest

from src.data.altitudes import AltitudeRepository

CSV_PATH = Path(__file__).parent.parent / "assets" / "data" / "wc2026_stadium_altitude.csv"


def test_loads_altitude_by_city():
    altitudes = AltitudeRepository(CSV_PATH).load()
    assert len(altitudes) == 16
    assert altitudes["Mexico City"] == 2240
    assert altitudes["New York/New Jersey"] == 7
    assert all(isinstance(v, int) for v in altitudes.values())


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("city,country\nDallas,USA\n")
    with pytest.raises(ValueError):
        AltitudeRepository(bad).load()


def test_non_numeric_altitude_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("city,altitude_m\nDallas,high\n")
    with pytest.raises(ValueError):
        AltitudeRepository(bad).load()
