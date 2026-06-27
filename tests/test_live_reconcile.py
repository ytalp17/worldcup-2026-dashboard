from __future__ import annotations

from src.data.matches import Match
from src.data.live.reconcile import (
    normalize, canonical_team, build_stadium_index, find_stadium, classify_stage,
)
from datetime import date, time, datetime, timezone


def _m(home, away, stadium):
    return Match(number=1, home=home, away=away, group="Group D",
                 stage="Group Stage", stadium=stadium, date=date(2026, 6, 12),
                 local_time=time(18, 0),
                 kickoff_utc=datetime.fromisoformat("2026-06-13T01:00:00+00:00"))


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  United   STATES ") == "united states"


def test_canonical_team_maps_bosnia_ampersand_to_official_and_spelling():
    # The live feed sends "Bosnia & Herzegovina"; the static/official name (and
    # the country_logos filename) uses "and". They must canonicalize the same.
    assert canonical_team("Bosnia & Herzegovina") == canonical_team("Bosnia and Herzegovina")


def test_find_stadium_exact_pair():
    index = build_stadium_index([_m("USA", "Paraguay", "Los Angeles Stadium")])
    assert find_stadium("USA", "Paraguay", index) == "Los Angeles Stadium"


def test_find_stadium_uses_alias():
    # Static schedule says "Türkiye"; a live feed might say "Turkey".
    index = build_stadium_index([_m("Australia", "Türkiye", "BC Place Vancouver")])
    assert find_stadium("Australia", "Turkey", index,
                        aliases={"turkey": "türkiye"}) == "BC Place Vancouver"


def test_find_stadium_unknown_pair_returns_none():
    index = build_stadium_index([_m("USA", "Paraguay", "Los Angeles Stadium")])
    assert find_stadium("Brazil", "Morocco", index) is None


def test_find_stadium_against_real_schedule():
    from pathlib import Path
    from src.data.matches import MatchRepository
    matches = MatchRepository(
        Path("assets/data/matches.csv")).load()
    index = build_stadium_index(matches)
    # Match #4 in the real schedule: USA vs Paraguay at Los Angeles Stadium.
    assert find_stadium("USA", "Paraguay", index) == "Los Angeles Stadium"


def test_index_matches_by_pair_keys_on_canonical_names():
    from src.data.live.reconcile import index_matches_by_pair, canonical_team
    api_matches = [
        {"match_id": 11, "home": "USA", "away": "Paraguay"},
        {"match_id": 22, "home": "South Korea", "away": "Czech Republic"},
    ]
    idx = index_matches_by_pair(api_matches)
    assert idx[("usa", "paraguay")] == 11
    # static names "Korea Republic"/"Czechia" canonicalize to the API spellings
    assert idx[(canonical_team("Korea Republic"), canonical_team("Czechia"))] == 22


def test_index_matches_by_pair_skips_incomplete():
    from src.data.live.reconcile import index_matches_by_pair
    idx = index_matches_by_pair([{"home": "USA", "away": "Paraguay"}])  # no match_id
    assert idx == {}


_KO = datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc)


def test_classify_stage_before_cutoff_is_group():
    assert classify_stage("2026-06-27T19:00:00+00:00", _KO) == "group"


def test_classify_stage_at_or_after_cutoff_is_knockout():
    assert classify_stage("2026-06-28T19:00:00+00:00", _KO) == "knockout"
    assert classify_stage("2026-07-01T19:00:00+00:00", _KO) == "knockout"


def test_classify_stage_accepts_datetime():
    dt = datetime(2026, 6, 28, 20, 0, tzinfo=timezone.utc)
    assert classify_stage(dt, _KO) == "knockout"


def test_classify_stage_missing_kickoff_defaults_group():
    assert classify_stage(None, _KO) == "group"
    assert classify_stage("not-a-date", _KO) == "group"


def test_classify_stage_no_cutoff_defaults_group():
    assert classify_stage("2026-08-01T19:00:00+00:00", None) == "group"
