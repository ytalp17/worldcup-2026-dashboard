from __future__ import annotations

from src.data.live.models import MatchState
from src.data.live.reconcile import build_stadium_index
from src.data.live.service import LiveDataService
from src.data.matches import Match
from datetime import date, time, datetime


def _m(home, away, stadium):
    return Match(number=1, home=home, away=away, group="G", stage="Group Stage",
                 stadium=stadium, date=date(2026, 6, 13), local_time=time(18, 0),
                 kickoff_utc=datetime.fromisoformat("2026-06-13T01:00:00+00:00"))


def _index():
    return build_stadium_index([
        _m("USA", "Paraguay", "Los Angeles Stadium"),
        _m("Brazil", "Mexico", "Dallas Stadium"),
    ])


class _FakeClient:
    def __init__(self):
        self.match_calls = 0

    def matches(self, date, league_id):
        self.match_calls += 1
        return {"data": [
            {"id": 1, "homeTeam": {"name": "USA"}, "awayTeam": {"name": "Paraguay"},
             "state": {"description": "Finished", "clock": 90,
                       "score": {"current": "4 - 1"}}},
            {"id": 2, "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Mexico"},
             "state": {"description": "Second Half", "clock": 67,
                       "score": {"current": "2 - 1"}}},
        ]}

    def standings(self, league_id, season):
        return {"groups": [
            {"name": "Group A", "standings": [
                {"team": {"name": "Mexico"}, "points": 3,
                 "total": {"games": 1, "wins": 1, "draws": 0, "loses": 0,
                           "scoredGoals": 2, "receivedGoals": 0}}]},
            {"name": "Group Stage", "standings": []},
        ]}


class _BoomClient:
    def matches(self, date, league_id):
        raise RuntimeError("network down")

    def standings(self, league_id, season):
        raise RuntimeError("network down")


def test_snapshot_shapes_matches_and_resolves_venue():
    svc = LiveDataService(_FakeClient(), _index())
    snap = svc.snapshot(date="2026-06-13", now=0.0)
    assert snap["ok"] is True
    assert snap["any_live"] is True            # Brazil-Mexico is Second Half
    by_id = {m["match_id"]: m for m in snap["matches"]}
    assert by_id[1]["venue"] == "Los Angeles Stadium"
    assert by_id[1]["state"] == MatchState.FINISHED.value
    assert by_id[1]["home_score"] == 4
    assert by_id[2]["venue"] == "Dallas Stadium"
    assert by_id[2]["is_live"] is True
    # Standings: rollup "Group Stage" excluded, Mexico present with computed GD.
    assert "Group Stage" not in snap["standings"]
    assert snap["standings"]["Group A"][0]["team"] == "Mexico"
    assert snap["standings"]["Group A"][0]["goal_diff"] == 2


def test_matches_cached_within_ttl():
    client = _FakeClient()
    svc = LiveDataService(client, _index())
    svc.snapshot(date="2026-06-13", now=0.0)
    svc.snapshot(date="2026-06-13", now=30.0)   # within 60s TTL
    assert client.match_calls == 1
    svc.snapshot(date="2026-06-13", now=90.0)   # past TTL
    assert client.match_calls == 2


def test_snapshot_falls_back_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    snap = svc.snapshot(date="2026-06-13", now=0.0)
    assert snap["ok"] is False
    assert snap["any_live"] is False
    assert snap["matches"] == []
    assert snap["standings"] == {}


def test_error_after_success_returns_last_good_marked_not_ok():
    class _Flaky(_FakeClient):
        def matches(self, date, league_id):
            if self.match_calls >= 1:
                self.match_calls += 1
                raise RuntimeError("down")
            return super().matches(date, league_id)
    client = _Flaky()
    svc = LiveDataService(client, _index())
    good = svc.snapshot(date="2026-06-13", now=0.0)
    assert good["ok"] is True
    bad = svc.snapshot(date="2026-06-13", now=999.0)  # past TTL -> refetch -> error
    assert bad["ok"] is False
    assert bad["matches"]  # last-good payload retained


def test_match_events_parses_and_caches():
    class _C(_FakeClient):
        def __init__(self):
            super().__init__()
            self.event_calls = 0

        def events(self, match_id):
            self.event_calls += 1
            return [{"minute": 67, "type": "Goal", "player": "Neymar", "team": "Brazil"},
                    {"minute": 12, "type": "Yellow Card", "player": "A", "team": "Mexico"}]

    c = _C()
    svc = LiveDataService(c, _index())
    evs = svc.match_events(42, now=0.0)
    assert [e["minute"] for e in evs] == [12, 67]   # sorted, dict form
    svc.match_events(42, now=10.0)                   # cached within TTL
    assert c.event_calls == 1


def test_match_events_empty_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    # _BoomClient has no events(); AttributeError is caught and returns [].
    assert svc.match_events(42, now=0.0) == []
