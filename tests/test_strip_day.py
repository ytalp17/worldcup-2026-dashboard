from __future__ import annotations
from datetime import date
from app import strip_day_matches

def test_today_uses_live_store():
    live = {"matches": [{"match_id": 1, "home": "A", "away": "B"}]}
    out = strip_day_matches("2026-06-13", date(2026, 6, 13), live, lambda d: [{"x": d}])
    assert out == live["matches"]

def test_other_day_uses_fetcher():
    out = strip_day_matches("2026-06-12", date(2026, 6, 13), {"matches": []},
                            lambda d: [{"match_id": 9, "day": d}])
    assert out == [{"match_id": 9, "day": "2026-06-12"}]

def test_no_fetcher_other_day_empty_falls_back_to_live():
    assert strip_day_matches("2026-06-12", date(2026, 6, 13), {}, None) == []

def test_bad_selected_date_falls_back_to_live():
    live = {"matches": [{"match_id": 1}]}
    assert strip_day_matches(None, date(2026, 6, 13), live, lambda d: [{"z": 1}]) == live["matches"]
