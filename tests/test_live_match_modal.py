from __future__ import annotations

from src.components.live_match_modal import modal_body, build_modal


def test_modal_body_shows_score_state_and_events():
    m = {"home": "Brazil", "away": "Mexico", "home_score": 2, "away_score": 1,
         "state": "live", "is_live": True, "clock": 67, "venue": "Dallas Stadium"}
    body = modal_body(m, events=[{"minute": 67, "type": "Goal",
                                  "player": "Neymar", "team": "Brazil"}])
    blob = str(body.to_plotly_json())
    assert "Brazil" in blob and "Mexico" in blob
    assert "2" in blob and "1" in blob
    assert "Neymar" in blob and "67" in blob
    assert "Dallas Stadium" in blob


def test_modal_body_handles_no_match_and_no_events():
    assert modal_body(None, events=[]) is not None
    body = modal_body({"home": "A", "away": "B", "home_score": None,
                       "away_score": None, "state": "scheduled", "clock": None},
                      events=[])
    assert "No events" in str(body.to_plotly_json())


def test_build_modal_closed_by_default():
    mod = build_modal()
    props = mod.to_plotly_json()["props"]
    assert props["id"] == "live-match-modal"
    assert props["opened"] is False
