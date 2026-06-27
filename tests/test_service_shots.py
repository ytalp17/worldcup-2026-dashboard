from src.data.live.service import LiveDataService
from src.data.live import models


class _Client:
    """Returns one match-detail object; records which match ids were fetched."""
    def __init__(self):
        self.fetched = []
        self.requests_remaining = 100

    def match(self, match_id):
        self.fetched.append(match_id)
        return [{
            "homeTeam": {"name": "England", "shots": [
                {"playerName": "A", "time": "10'", "outcome": "Goal",
                 "goalTarget": "Low Centre"},
                {"playerName": "B", "time": "20'", "outcome": "Missed",
                 "goalTarget": None}]},
            "awayTeam": {"name": "Wales", "shots": [
                {"playerName": "C", "time": "30'", "outcome": "Saved",
                 "goalTarget": "High Right"}]},
        }]


def _svc(tmp_path):
    return LiveDataService(_Client(), stadium_index={},
                           shots_store=tmp_path / "live_shots.csv")


def test_update_then_aggregate_for_team(tmp_path):
    svc = _svc(tmp_path)
    matches = [{"match_id": 5, "state": models.MatchState.FINISHED.value,
                "kickoff": "2026-06-15T18:00:00+00:00"}]
    svc.update_shot_stats(matches, now=1.0)
    agg = svc.team_goal_mouth("England")
    assert agg["zones"]["low_centre"]["count"] == 1
    assert agg["off_target"]["count"] == 1
    assert agg["totals"]["total"] == 2          # England's two shots only


def test_finished_and_stored_is_skipped(tmp_path):
    svc = _svc(tmp_path)
    matches = [{"match_id": 5, "state": models.MatchState.FINISHED.value,
                "kickoff": "2026-06-15T18:00:00+00:00"}]
    svc.update_shot_stats(matches, now=1.0)
    svc.update_shot_stats(matches, now=2.0)     # already finished+stored
    assert svc._client.fetched == [5]           # fetched once, not twice


def test_no_store_returns_empty_structure():
    svc = LiveDataService(_Client(), stadium_index={})   # shots_store=None
    agg = svc.team_goal_mouth("England")
    assert agg["totals"]["total"] == 0
    assert set(agg["zones"]) >= {"low_centre", "high_left"}
