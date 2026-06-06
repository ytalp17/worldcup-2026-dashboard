from pathlib import Path
from src.data.squads import Player, Squad, SquadRepository, squad_for_team

CSV = Path(__file__).parent.parent / "assets" / "data" / "world_cup_2026_squads.csv"


def _load():
    return SquadRepository(CSV).load()


def test_loads_all_48_teams_keyed_by_canonical_name():
    squads = _load()
    assert len(squads) == 48
    assert "Korea Republic" in squads
    assert "South Korea" not in squads
    assert "Brazil" in squads


def test_all_overrides_resolve():
    squads = _load()
    for canonical in [
        "Bosnia and Herzegovina", "Cabo Verde", "Curaçao", "Czechia",
        "Congo DR", "IR Iran", "Côte d'Ivoire", "Korea Republic",
        "Türkiye", "USA",
    ]:
        assert canonical in squads, canonical


def test_squad_has_players_with_expected_fields():
    squad = _load()["Canada"]
    assert isinstance(squad, Squad)
    assert squad.name == "Canada"
    assert 23 <= len(squad.players) <= 30
    p = next(pl for pl in squad.players if pl.name == "Alphonso Davies")
    assert isinstance(p, Player)
    assert p.number == 19
    assert p.position == "Left-Back"
    assert p.club == "Bayern Munich"
    assert p.height_m == "1.83"
    assert p.foot == "left"
    assert p.market_value == "€40.00m"


def test_blank_caps_tolerated():
    squad = _load()["Canada"]
    p = next(pl for pl in squad.players if pl.name == "Owen Goodman")
    assert p.caps == ""


def test_squad_for_team():
    squads = _load()
    assert squad_for_team(squads, "Korea Republic").name == "Korea Republic"
    assert squad_for_team(squads, "Nowhere") is None
