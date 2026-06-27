from __future__ import annotations

import json
from pathlib import Path

from src.components.live_match_modal import (
    build_modal,
    event_visual,
    loading_body,
    modal_body,
    stat_rows,
)
from src.data.live.models import parse_statistics

FIXTURES = Path(__file__).parent / "fixtures" / "live"


# ---------------------------------------------------------------------------
# stat_rows helper
# ---------------------------------------------------------------------------

class TestStatRows:
    def setup_method(self):
        raw = json.loads((FIXTURES / "finished_statistics.json").read_text())
        self.stats = parse_statistics(raw)
        self.rows = stat_rows(self.stats, "USA", "Paraguay")

    def test_returns_list_of_tuples(self):
        assert isinstance(self.rows, list)
        for row in self.rows:
            assert isinstance(row, tuple)
            assert len(row) == 4  # (label, home_display, away_display, home_is_larger)

    def test_possession_row_home_65_pct(self):
        possession = next(r for r in self.rows if r[0] == "Possession")
        assert possession[1] == "65%"    # home display
        assert possession[2] == "35%"    # away display

    def test_possession_home_is_larger(self):
        possession = next(r for r in self.rows if r[0] == "Possession")
        assert possession[3] is True     # USA has more possession

    def test_fouls_row_home_13(self):
        fouls = next(r for r in self.rows if r[0] == "Fouls")
        assert fouls[1] == "13"

    def test_xg_row_formatted_to_2dp(self):
        xg = next(r for r in self.rows if r[0] == "xG")
        assert xg[1] == "1.42"

    def test_curated_stats_present(self):
        labels = [r[0] for r in self.rows]
        for expected in ("Possession", "Shots", "Shots on target", "xG", "Fouls", "Corners"):
            assert expected in labels

    def test_empty_stats_returns_empty_list(self):
        assert stat_rows({}, "A", "B") == []


# ---------------------------------------------------------------------------
# event_visual — emoji + accent colour per event type
# ---------------------------------------------------------------------------

class TestEventVisual:
    def test_goal(self):
        assert event_visual("Goal") == ("⚽", "green")

    def test_penalty_is_green(self):
        assert event_visual("Penalty")[1] == "green"

    def test_own_goal_is_red(self):
        emoji, color = event_visual("Own Goal")
        assert color == "red"

    def test_yellow_card(self):
        assert event_visual("Yellow Card") == ("🟨", "yellow")

    def test_red_card_is_red(self):
        assert event_visual("Red Card")[1] == "red"

    def test_substitution_variant_is_blue(self):
        # real API may send lowercase / variant spellings
        assert event_visual("substitution")[1] == "blue"

    def test_var_variant_is_grape(self):
        assert event_visual("VAR Goal Cancelled - Offside")[1] == "grape"

    def test_unknown_type_falls_back_to_default(self):
        assert event_visual("Kickoff") == ("🔹", "gray")

    def test_empty_type_falls_back_to_default(self):
        assert event_visual("") == ("🔹", "gray")


# ---------------------------------------------------------------------------
# Timeline tab — one card per event
# ---------------------------------------------------------------------------

class TestTimelineCards:
    def setup_method(self):
        self.events = [
            {"minute": 23, "type": "Goal", "player": "Messi", "team": "Argentina"},
            {"minute": 45, "type": "Yellow Card", "player": "Casemiro", "team": "Brazil"},
        ]
        self.match = {
            "home": "Argentina", "away": "Brazil",
            "home_score": 1, "away_score": 0,
            "state": "live", "is_live": True, "clock": 60,
        }
        self.body = modal_body(self.match, self.events, {}, {})
        self.blob = str(self.body.to_plotly_json())

    def test_renders_one_card_per_event(self):
        assert self.blob.count("tl-event-card") == 2

    def test_shows_event_emojis(self):
        assert "⚽" in self.blob
        assert "🟨" in self.blob

    def test_shows_player_and_team(self):
        assert "Messi" in self.blob and "Argentina" in self.blob
        assert "Casemiro" in self.blob and "Brazil" in self.blob

    def test_shows_minute(self):
        assert "23'" in self.blob and "45'" in self.blob


# ---------------------------------------------------------------------------
# modal_body — full tabbed body
# ---------------------------------------------------------------------------

class TestModalBodyTabbed:
    def setup_method(self):
        raw_stats = json.loads((FIXTURES / "finished_statistics.json").read_text())
        raw_events = json.loads((FIXTURES / "finished_events.json").read_text())
        raw_lineups = json.loads((FIXTURES / "finished_lineups.json").read_text())

        from src.data.live.models import parse_events, parse_lineups, parse_statistics
        self.stats = parse_statistics(raw_stats)
        self.events = [vars(e) for e in parse_events(raw_events)]
        self.lineups = parse_lineups(raw_lineups)

        self.match = {
            "home": "USA", "away": "Paraguay",
            "home_score": 4, "away_score": 1,
            "state": "finished", "is_live": False, "clock": 90,
            "venue": "Los Angeles Stadium",
        }
        self.body = modal_body(self.match, self.events, self.stats, self.lineups)

    def test_body_renders_to_json(self):
        blob = str(self.body.to_plotly_json())
        assert blob  # non-empty

    def test_contains_possession(self):
        blob = str(self.body.to_plotly_json())
        assert "Possession" in blob

    def test_contains_player_from_timeline(self):
        blob = str(self.body.to_plotly_json())
        # D. Bobadilla is in the fixture events
        assert "D. Bobadilla" in blob or "Bobadilla" in blob

    def test_contains_matthew_freese_from_lineups(self):
        blob = str(self.body.to_plotly_json())
        assert "Matthew Freese" in blob

    def test_contains_score(self):
        blob = str(self.body.to_plotly_json())
        assert "4" in blob and "1" in blob

    def test_contains_venue(self):
        blob = str(self.body.to_plotly_json())
        assert "Los Angeles Stadium" in blob


# ---------------------------------------------------------------------------
# modal_body — edge cases
# ---------------------------------------------------------------------------

def test_modal_body_no_match():
    body = modal_body(None, [], {}, {})
    assert "No match selected" in str(body.to_plotly_json())


def test_modal_body_empty_stats_shows_no_stats_message():
    m = {"home": "A", "away": "B", "home_score": 0, "away_score": 0,
         "state": "scheduled", "is_live": False, "clock": None}
    body = modal_body(m, [], {}, {})
    blob = str(body.to_plotly_json())
    assert "No statistics" in blob


def test_modal_body_empty_events_shows_no_events_message():
    m = {"home": "A", "away": "B", "home_score": 0, "away_score": 0,
         "state": "live", "is_live": True, "clock": 10}
    body = modal_body(m, [], {}, {})
    blob = str(body.to_plotly_json())
    assert "No events" in blob


def test_modal_body_empty_lineups_shows_not_available():
    m = {"home": "A", "away": "B", "home_score": 0, "away_score": 0,
         "state": "live", "is_live": True, "clock": 10}
    body = modal_body(m, [], {}, {})
    blob = str(body.to_plotly_json())
    assert "not available" in blob.lower() or "Lineups not available" in blob


# ---------------------------------------------------------------------------
# build_modal
# ---------------------------------------------------------------------------

def test_build_modal_closed_by_default():
    mod = build_modal()
    props = mod.to_plotly_json()["props"]
    assert props["id"] == "live-match-modal"
    assert props["opened"] is False


def test_build_modal_size_and_z_index():
    mod = build_modal()
    props = mod.to_plotly_json()["props"]
    assert props.get("size") == "lg"
    assert props.get("zIndex") == 3000


# ---------------------------------------------------------------------------
# Two-phase open: instant skeleton + stable content container
# ---------------------------------------------------------------------------

def test_build_modal_wraps_content_in_stable_container():
    # The body lives in a fixed #live-modal-content div the fill callback targets.
    assert "live-modal-content" in str(build_modal().to_plotly_json())


def test_loading_body_is_skeleton_placeholder():
    blob = str(loading_body().to_plotly_json())
    # Several skeletons mimicking the real layout (title, badge, tabs, rows).
    assert blob.count("Skeleton") >= 8
