import pytest

from src.data.distances import DistanceRepository


def test_loads_distance_by_team(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("team,distance_km\nBrazil,1839.7\nMexico,420.0\n")
    distances = DistanceRepository(csv).load()
    assert distances == {"Brazil": 1839.7, "Mexico": 420.0}
    assert all(isinstance(v, float) for v in distances.values())


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("team,foo\nBrazil,1\n")
    with pytest.raises(ValueError):
        DistanceRepository(bad).load()


def test_non_numeric_distance_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("team,distance_km\nBrazil,far\n")
    with pytest.raises(ValueError):
        DistanceRepository(bad).load()
