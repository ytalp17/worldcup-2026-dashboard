from src.data.squads import Player, Squad
from src.data.team_stats import (
    TeamStats,
    compute_team_stats,
    format_value,
    parse_market_value,
)


def _player(age="25", height="1.80", foot="right", mv="€1.00m"):
    return Player(
        number=1, name="X", position="Centre-Back", dob="", age=age,
        club="", height_m=height, foot=foot, caps="", goals="", debut="",
        market_value=mv,
    )


def test_parse_market_value():
    assert parse_market_value("€1.60m") == 1_600_000.0
    assert parse_market_value("€700k") == 700_000.0
    assert parse_market_value("€2.00m") == 2_000_000.0
    assert parse_market_value("") == 0.0
    assert parse_market_value("n/a") == 0.0


def test_format_value():
    assert format_value(3_000_000) == "€3M"
    assert format_value(700_000) == "€700K"
    assert format_value(1_200_000_000) == "€1.2B"
    assert format_value(0) == "€0"


def test_compute_team_stats():
    squad = Squad("Test", (
        _player(age="30", height="1.80", foot="right", mv="€1.50m"),
        _player(age="20", height="1.90", foot="left", mv="€500k"),
        _player(age="25", height="1.70", foot="right", mv="€1.00m"),
    ))
    stats = compute_team_stats(squad)
    assert isinstance(stats, TeamStats)
    assert stats.avg_age == 25.0
    assert stats.avg_height == 1.8
    assert stats.value_display == "€3M"
    assert stats.foot_right_pct == 67
    assert stats.foot_left_pct == 33
    assert stats.squad_size == 3
    # No data sources yet for these.
    assert stats.fifa_rank is None
    assert stats.manager is None
    assert stats.abroad is None


def test_compute_team_stats_is_division_safe():
    stats = compute_team_stats(Squad("Empty", ()))
    assert stats.avg_age is None
    assert stats.avg_height is None
    assert stats.squad_size == 0
    assert stats.value_display == "€0"


def test_compute_team_stats_ignores_blank_cells():
    squad = Squad("Test", (
        _player(age="30", height="1.80"),
        _player(age="", height="", foot="", mv=""),  # all blank — skipped
    ))
    stats = compute_team_stats(squad)
    assert stats.avg_age == 30.0
    assert stats.avg_height == 1.8
    assert stats.squad_size == 2


def test_compute_team_stats_passes_through_rank_and_manager():
    stats = compute_team_stats(
        Squad("Brazil", (_player(),)), fifa_rank=6, manager="Carlo Ancelotti")
    assert stats.fifa_rank == 6
    assert stats.manager == "Carlo Ancelotti"


def test_compute_team_stats_rank_and_manager_default_none():
    stats = compute_team_stats(Squad("X", (_player(),)))
    assert stats.fifa_rank is None and stats.manager is None


def test_compute_team_stats_passes_manager_nationality_and_flag():
    stats = compute_team_stats(
        Squad("Brazil", (_player(),)),
        manager="Carlo Ancelotti",
        manager_nationality="Italy",
        manager_flag="/assets/manager_flags/Italy.png",
    )
    assert stats.manager_nationality == "Italy"
    assert stats.manager_flag == "/assets/manager_flags/Italy.png"


def test_compute_team_stats_manager_extras_default_none():
    stats = compute_team_stats(Squad("X", (_player(),)))
    assert stats.manager_nationality is None and stats.manager_flag is None


def test_compute_team_stats_passes_manager_age():
    stats = compute_team_stats(Squad("Brazil", (_player(),)), manager_age=67)
    assert stats.manager_age == 67


def test_compute_team_stats_manager_age_default_none():
    assert compute_team_stats(Squad("X", (_player(),))).manager_age is None
