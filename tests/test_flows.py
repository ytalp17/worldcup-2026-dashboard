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


def _flows():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    return build_team_flows(matches, venues)


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
