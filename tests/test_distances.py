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


from pathlib import Path

from src.data.flows import build_team_flows, path_distance_km
from src.data.host_cities import HostCityRepository
from src.data.matches import MatchRepository
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
CSV_PATH = DATA / "team_distances.csv"


def test_csv_matches_recomputed_distances():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    flows = build_team_flows(matches, venues)

    on_disk = DistanceRepository(CSV_PATH).load()
    assert set(on_disk) == set(flows)
    assert len(on_disk) == 48
    for team, flow in flows.items():
        assert abs(on_disk[team] - path_distance_km(flow.stops)) < 0.1
