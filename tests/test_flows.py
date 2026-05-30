from datetime import date
from pathlib import Path

import pytest

from src.data.flows import FlowStop, TeamFlow, build_team_flows, team_color
from src.data.host_cities import HostCityRepository
from src.data.matches import Match, MatchRepository
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"


def _venues():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    return build_venues(cities, stadiums, IMAGE_DIR)


def _flows():
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    return build_team_flows(matches, _venues())


def test_team_color_is_deterministic_and_hex():
    assert team_color("Brazil") == team_color("Brazil")
    assert team_color("Brazil").startswith("#") and len(team_color("Brazil")) == 7
    assert team_color("Brazil") != team_color("Argentina")


def test_builds_a_flow_per_group_stage_team():
    flows = _flows()
    assert len(flows) == 48
    assert all(isinstance(f, TeamFlow) for f in flows.values())


def test_brazil_flow_stops_in_chronological_order():
    flows = _flows()
    brazil = flows["Brazil"]
    assert brazil.continent == "South America"
    assert brazil.color == team_color("Brazil")
    names = [s.stadium_name for s in brazil.stops]
    assert names == ["New York New Jersey Stadium", "Philadelphia Stadium", "Miami Stadium"]
    dates = [s.date for s in brazil.stops]
    assert dates == sorted(dates)
    assert all(isinstance(s, FlowStop) for s in brazil.stops)


def test_mexico_flow_doubles_back():
    flows = _flows()
    stops = flows["Mexico"].stops
    assert (stops[0].lat, stops[0].lon) == (stops[2].lat, stops[2].lon)


def test_unmatched_stadium_raises():
    bad = [Match(1, "Brazil", "X", "Group A", "Group Stage", "Nowhere Stadium", date(2026, 6, 11))]
    with pytest.raises(ValueError):
        build_team_flows(bad, [])


def test_build_team_flows_stamps_distance_from_dict():
    flows = build_team_flows(
        MatchRepository(DATA / "wc2026_matches.csv").load(),
        _venues(),
        distances={"Brazil": 1839.7},
    )
    assert flows["Brazil"].distance_km == 1839.7
    # A team absent from the dict keeps the default.
    assert flows["Mexico"].distance_km == 0.0


def test_build_team_flows_distance_defaults_to_zero():
    assert all(f.distance_km == 0.0 for f in _flows().values())


from src.data.flows import haversine_km, path_distance_km


def test_haversine_zero_for_same_point():
    assert haversine_km(40.0, -74.0, 40.0, -74.0) == 0.0


def test_haversine_known_pair_nyc_to_la():
    # NYC (40.7128,-74.0060) -> LA (34.0522,-118.2437) ~= 3936 km
    d = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert abs(d - 3936) < 20


def test_path_distance_sums_consecutive_legs():
    stops = (
        FlowStop(40.7128, -74.0060, "A", date(2026, 6, 1), 1),
        FlowStop(34.0522, -118.2437, "B", date(2026, 6, 2), 2),
        FlowStop(40.7128, -74.0060, "C", date(2026, 6, 3), 3),
    )
    leg = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert abs(path_distance_km(stops) - 2 * leg) < 1e-6


def test_path_distance_zero_or_one_stop_is_zero():
    assert path_distance_km(()) == 0.0
    assert path_distance_km((FlowStop(0, 0, "A", date(2026, 6, 1), 1),)) == 0.0
