from __future__ import annotations

from src.data.matches import Match
from src.data.live.reconcile import (
    normalize, canonical_team, build_stadium_index, find_stadium,
)
from datetime import date, time, datetime


def _m(home, away, stadium):
    return Match(number=1, home=home, away=away, group="Group D",
                 stage="Group Stage", stadium=stadium, date=date(2026, 6, 12),
                 local_time=time(18, 0),
                 kickoff_utc=datetime.fromisoformat("2026-06-13T01:00:00+00:00"))


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  United   STATES ") == "united states"


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
        Path("assets/data/wc2026_matches.csv")).load()
    index = build_stadium_index(matches)
    # Match #4 in the real schedule: USA vs Paraguay at Los Angeles Stadium.
    assert find_stadium("USA", "Paraguay", index) == "Los Angeles Stadium"
