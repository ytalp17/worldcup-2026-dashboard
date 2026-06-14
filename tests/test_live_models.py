"""Tests for src/data/live/models.py — parse Highlightly JSON into typed dataclasses.

Tests run against real captured fixtures in tests/fixtures/live/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data.live.models import (
    LiveMatch,
    MatchEvent,
    MatchState,
    Standing,
    parse_events,
    parse_lineups,
    parse_match,
    parse_matches,
    parse_standings,
    parse_statistics,
)

FIXTURES = Path(__file__).parent / "fixtures" / "live"


# ---------------------------------------------------------------------------
# parse_matches — real fixture
# ---------------------------------------------------------------------------

class TestParseMatchesFromFixture:
    def setup_method(self):
        raw = json.loads((FIXTURES / "matches.json").read_text())
        self.raw = raw
        self.matches = parse_matches(raw)

    def test_returns_list_of_live_match(self):
        assert all(isinstance(m, LiveMatch) for m in self.matches)

    def test_length_equals_data_rows(self):
        expected = len(self.raw["data"])
        assert len(self.matches) == expected  # 3 matches in fixture

    def test_finished_match_usa_paraguay(self):
        # USA vs Paraguay, score "4 - 1", state Finished
        finished = next(
            m for m in self.matches if m.home == "USA" and m.away == "Paraguay"
        )
        assert finished.state is MatchState.FINISHED
        assert finished.home_score == 4
        assert finished.away_score == 1

    def test_finished_match_is_not_live(self):
        finished = next(m for m in self.matches if m.home == "USA")
        assert finished.is_live is False

    def test_not_started_match_brazil_morocco(self):
        # Brazil vs Morocco — "Not started", no score
        not_started = next(
            m for m in self.matches if m.home == "Brazil" and m.away == "Morocco"
        )
        assert not_started.state is MatchState.SCHEDULED
        assert not_started.home_score is None
        assert not_started.away_score is None

    def test_not_started_match_is_not_live(self):
        not_started = next(m for m in self.matches if m.home == "Brazil")
        assert not_started.is_live is False

    def test_match_ids_are_ints(self):
        for m in self.matches:
            assert isinstance(m.match_id, int)


# ---------------------------------------------------------------------------
# parse_match — inline live-state dict
# ---------------------------------------------------------------------------

class TestParseMatchInline:
    RAW_LIVE = {
        "id": 42,
        "homeTeam": {"name": "Brazil"},
        "awayTeam": {"name": "Mexico"},
        "state": {
            "description": "Second Half",
            "clock": 67,
            "score": {"current": "2 - 1"},
        },
    }

    def test_returns_live_match(self):
        m = parse_match(self.RAW_LIVE)
        assert isinstance(m, LiveMatch)

    def test_match_id(self):
        m = parse_match(self.RAW_LIVE)
        assert m.match_id == 42

    def test_team_names(self):
        m = parse_match(self.RAW_LIVE)
        assert m.home == "Brazil"
        assert m.away == "Mexico"

    def test_state_is_live(self):
        m = parse_match(self.RAW_LIVE)
        assert m.state is MatchState.LIVE

    def test_clock(self):
        m = parse_match(self.RAW_LIVE)
        assert m.clock == 67

    def test_scores_parsed(self):
        m = parse_match(self.RAW_LIVE)
        assert m.home_score == 2
        assert m.away_score == 1

    def test_is_live_true(self):
        m = parse_match(self.RAW_LIVE)
        assert m.is_live is True

    def test_halftime_state(self):
        raw = {
            "id": 99,
            "homeTeam": {"name": "A"},
            "awayTeam": {"name": "B"},
            "state": {"description": "Halftime", "clock": 45, "score": {"current": "1 - 0"}},
        }
        m = parse_match(raw)
        assert m.state is MatchState.HALF_TIME
        assert m.is_live is True


# ---------------------------------------------------------------------------
# parse_standings — real fixture
# ---------------------------------------------------------------------------

class TestParseStandingsFromFixture:
    def setup_method(self):
        raw = json.loads((FIXTURES / "standings.json").read_text())
        self.standings = parse_standings(raw)

    def test_returns_dict(self):
        assert isinstance(self.standings, dict)

    def test_group_stage_rollup_skipped(self):
        assert "Group Stage" not in self.standings

    def test_twelve_real_groups(self):
        assert len(self.standings) == 12

    def test_expected_group_keys(self):
        for letter in "ABCDEFGHIJKL":
            assert f"Group {letter}" in self.standings

    def test_group_a_leader_is_mexico(self):
        # Group A: Mexico leads with 3 points (1 win, scored 2, received 0)
        rows = self.standings["Group A"]
        assert rows[0].team == "Mexico"
        assert rows[0].points == 3

    def test_group_a_leader_goal_diff(self):
        # Mexico: scoredGoals=2, receivedGoals=0 → goal_diff=2
        rows = self.standings["Group A"]
        assert rows[0].goal_diff == 2

    def test_group_d_leader_is_usa(self):
        # Group D: USA leads with 3 points (scored 4, received 1)
        rows = self.standings["Group D"]
        assert rows[0].team == "USA"
        assert rows[0].points == 3
        assert rows[0].goal_diff == 3  # 4 - 1

    def test_standings_are_standing_instances(self):
        for group_rows in self.standings.values():
            for row in group_rows:
                assert isinstance(row, Standing)

    def test_group_a_has_four_teams(self):
        assert len(self.standings["Group A"]) == 4

    def test_south_korea_in_group_a(self):
        teams = [r.team for r in self.standings["Group A"]]
        assert "South Korea" in teams


# ---------------------------------------------------------------------------
# parse_events
# ---------------------------------------------------------------------------

class TestParseEvents:
    RAW_EVENTS = [
        {"minute": 67, "type": "Goal", "player": "Neymar", "team": "Brazil"},
        {"minute": 12, "type": "Yellow Card", "player": "Alvarez", "team": "Mexico"},
    ]

    def test_returns_list_of_match_event(self):
        events = parse_events(self.RAW_EVENTS)
        assert all(isinstance(e, MatchEvent) for e in events)

    def test_sorted_by_minute_ascending(self):
        events = parse_events(self.RAW_EVENTS)
        assert [e.minute for e in events] == [12, 67]

    def test_event_fields(self):
        events = parse_events(self.RAW_EVENTS)
        yellow = events[0]
        assert yellow.minute == 12
        assert yellow.type == "Yellow Card"
        assert yellow.player == "Alvarez"
        assert yellow.team == "Mexico"

        goal = events[1]
        assert goal.minute == 67
        assert goal.type == "Goal"
        assert goal.player == "Neymar"
        assert goal.team == "Brazil"

    def test_empty_input_returns_empty_list(self):
        assert parse_events([]) == []

    def test_none_input_returns_empty_list(self):
        assert parse_events(None) == []


# ---------------------------------------------------------------------------
# parse_events — real fixture (new schema: time/team.name)
# ---------------------------------------------------------------------------

class TestParseEventsFromFixture:
    def setup_method(self):
        raw = json.loads((FIXTURES / "finished_events.json").read_text())
        self.raw = raw
        self.events = parse_events(raw)

    def test_length_is_21(self):
        assert len(self.events) == 21

    def test_first_event_in_fixture_has_minute_7(self):
        # original order: first event has time="7" and team.name="USA"
        # after parse it should have minute=7
        by_minute = {e.minute: e for e in self.events}
        assert 7 in by_minute

    def test_first_event_team_is_string_not_dict(self):
        # team must be "USA", not a dict
        evt_at_7 = next(e for e in self.events if e.minute == 7)
        assert evt_at_7.team == "USA"
        assert isinstance(evt_at_7.team, str)

    def test_sorted_ascending_by_minute(self):
        minutes = [e.minute for e in self.events]
        assert minutes == sorted(minutes)

    def test_no_event_has_minute_0(self):
        # The fixture has no 0-minute events; the bug caused all minutes to be 0
        assert all(e.minute != 0 for e in self.events)

    def test_first_event_player_is_d_bobadilla(self):
        evt_at_7 = next(e for e in self.events if e.minute == 7)
        assert evt_at_7.player == "D. Bobadilla"
        assert evt_at_7.type == "Own Goal"


# ---------------------------------------------------------------------------
# parse_statistics — real fixture
# ---------------------------------------------------------------------------

class TestParseStatisticsFromFixture:
    def setup_method(self):
        raw = json.loads((FIXTURES / "finished_statistics.json").read_text())
        self.stats = parse_statistics(raw)

    def test_returns_dict_with_two_teams(self):
        assert isinstance(self.stats, dict)
        assert len(self.stats) == 2

    def test_usa_possession(self):
        assert self.stats["USA"]["Possession"] == 0.65

    def test_usa_fouls(self):
        assert self.stats["USA"]["Fouls"] == 13

    def test_paraguay_possession(self):
        assert self.stats["Paraguay"]["Possession"] == 0.35

    def test_usa_expected_goals(self):
        assert self.stats["USA"]["Expected Goals"] == 1.42

    def test_team_keys_are_strings(self):
        for key in self.stats:
            assert isinstance(key, str)


# ---------------------------------------------------------------------------
# parse_lineups — real fixture
# ---------------------------------------------------------------------------

class TestParseLineupsFromFixture:
    def setup_method(self):
        raw = json.loads((FIXTURES / "finished_lineups.json").read_text())
        self.lineups = parse_lineups(raw)

    def test_returns_dict_with_home_and_away(self):
        assert "home" in self.lineups
        assert "away" in self.lineups

    def test_home_formation(self):
        assert self.lineups["home"]["formation"] == "4-2-3-1"

    def test_home_has_11_starters(self):
        assert len(self.lineups["home"]["starters"]) == 11

    def test_home_first_starter_is_matthew_freese(self):
        assert self.lineups["home"]["starters"][0]["name"] == "Matthew Freese"

    def test_starter_has_required_fields(self):
        starter = self.lineups["home"]["starters"][0]
        assert "name" in starter
        assert "number" in starter
        assert "position" in starter

    def test_home_has_subs(self):
        assert len(self.lineups["home"]["subs"]) > 0

    def test_missing_data_returns_defaults(self):
        result = parse_lineups({})
        assert result["home"] == {"formation": "", "starters": [], "subs": []}
        assert result["away"] == {"formation": "", "starters": [], "subs": []}


def test_parse_match_reads_kickoff_utc():
    from src.data.live.models import parse_match
    raw = {"id": 5, "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Mexico"},
           "date": "2026-06-13T22:00:00.000Z", "state": {}}
    m = parse_match(raw)
    assert m.kickoff is not None and m.kickoff.tzinfo is not None
    assert m.kickoff.hour == 22


def test_parse_match_kickoff_none_when_missing():
    from src.data.live.models import parse_match
    m = parse_match({"id": 5, "homeTeam": {"name": "A"},
                     "awayTeam": {"name": "B"}, "state": {}})
    assert m.kickoff is None
