from pathlib import Path

from src.data.lineups import (
    LineupRepository,
    StartingEleven,
    canonical_team,
    format_formation,
    lineup_for_team,
)

DATA = Path("assets/data/estimated_starting_eleven.json")


def test_canonical_team_renames():
    assert canonical_team("south-korea") == "Korea Republic"
    assert canonical_team("ivory-coast") == "Côte d'Ivoire"
    assert canonical_team("iran") == "IR Iran"
    assert canonical_team("turkiye") == "Türkiye"
    assert canonical_team("dr-congo") == "Congo DR"
    assert canonical_team("cape-verde") == "Cabo Verde"
    assert canonical_team("curacao") == "Curaçao"
    assert canonical_team("bosnia-and-herzegovina") == "Bosnia and Herzegovina"
    assert canonical_team("usa") == "USA"
    # Plain slugs fall back to a title-cased name.
    assert canonical_team("brazil") == "Brazil"
    assert canonical_team("new-zealand") == "New Zealand"


def test_format_formation():
    assert format_formation("433") == "4-3-3"
    assert format_formation("4231") == "4-2-3-1"
    assert format_formation("3421") == "3-4-2-1"


def test_repository_loads_all_48():
    lineups = LineupRepository(DATA).load()
    assert len(lineups) == 48
    arg = lineups["Argentina"]
    assert isinstance(arg, StartingEleven)
    assert arg.team == "Argentina"
    assert arg.slug == "argentina"
    assert arg.formation == "433"
    assert len(arg.xi) == 11
    name, number = arg.xi[0]
    assert isinstance(name, str) and isinstance(number, int)


def test_repository_uses_canonical_keys():
    lineups = LineupRepository(DATA).load()
    # Keyed by the app's canonical FIFA names, not the scrape slugs/labels.
    assert "Korea Republic" in lineups
    assert "Côte d'Ivoire" in lineups
    assert "south-korea" not in lineups
    assert lineups["Korea Republic"].slug == "south-korea"


def test_lineup_for_team_hit_and_miss():
    lineups = LineupRepository(DATA).load()
    assert lineup_for_team(lineups, "Korea Republic").slug == "south-korea"
    assert lineup_for_team(lineups, "Nowhere") is None
