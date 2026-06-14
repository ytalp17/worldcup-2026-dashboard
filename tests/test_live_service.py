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


# ---------------------------------------------------------------------------
# match_statistics
# ---------------------------------------------------------------------------

def test_match_statistics_parses_and_caches():
    class _C(_FakeClient):
        def __init__(self):
            super().__init__()
            self.stats_calls = 0

        def statistics(self, match_id):
            self.stats_calls += 1
            return [
                {"team": {"name": "USA"}, "statistics": [
                    {"displayName": "Possession", "value": 0.65},
                    {"displayName": "Fouls", "value": 13},
                ]},
                {"team": {"name": "Paraguay"}, "statistics": [
                    {"displayName": "Possession", "value": 0.35},
                    {"displayName": "Fouls", "value": 17},
                ]},
            ]

    c = _C()
    svc = LiveDataService(c, _index())
    result = svc.match_statistics(42, now=0.0)
    assert isinstance(result, dict)
    assert result["USA"]["Possession"] == 0.65
    assert result["USA"]["Fouls"] == 13
    assert result["Paraguay"]["Possession"] == 0.35
    # Cached within TTL — no second call
    svc.match_statistics(42, now=10.0)
    assert c.stats_calls == 1


def test_match_statistics_empty_dict_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.match_statistics(42, now=0.0) == {}


# ---------------------------------------------------------------------------
# match_lineups
# ---------------------------------------------------------------------------

def test_match_lineups_parses_and_caches():
    class _C(_FakeClient):
        def __init__(self):
            super().__init__()
            self.lineup_calls = 0

        def lineups(self, match_id):
            self.lineup_calls += 1
            return {
                "homeTeam": {
                    "formation": "4-2-3-1",
                    "initialLineup": [[{"name": "Matthew Freese", "number": 24, "position": "Goalkeeper"}]],
                    "substitutes": [{"name": "Matt Turner", "number": 1, "position": "Goalkeeper"}],
                    "name": "USA",
                },
                "awayTeam": {
                    "formation": "4-4-2",
                    "initialLineup": [[{"name": "Antony Silva", "number": 1, "position": "Goalkeeper"}]],
                    "substitutes": [],
                    "name": "Paraguay",
                },
            }

    c = _C()
    svc = LiveDataService(c, _index())
    result = svc.match_lineups(42, now=0.0)
    assert isinstance(result, dict)
    assert result["home"]["formation"] == "4-2-3-1"
    assert result["home"]["starters"][0]["name"] == "Matthew Freese"
    assert len(result["home"]["subs"]) == 1
    # Cached within TTL
    svc.match_lineups(42, now=10.0)
    assert c.lineup_calls == 1


def test_match_lineups_empty_dict_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.match_lineups(42, now=0.0) == {}


# ---------------------------------------------------------------------------
# matches_on
# ---------------------------------------------------------------------------

def test_matches_on_returns_day_match_dicts_and_caches():
    client = _FakeClient()
    svc = LiveDataService(client, _index())
    out = svc.matches_on("2026-06-12", now=0.0)
    assert {m["home"] for m in out} == {"USA", "Brazil"}
    svc.matches_on("2026-06-12", now=10.0)        # cached (same date)
    assert client.match_calls == 1
    svc.matches_on("2026-06-13", now=20.0)        # different date -> new fetch
    assert client.match_calls == 2


def test_matches_on_empty_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.matches_on("2026-06-12", now=0.0) == []


# ---------------------------------------------------------------------------
# match_summary
# ---------------------------------------------------------------------------

def test_match_summary_parses_detail_and_caches():
    class _C(_FakeClient):
        def __init__(self):
            super().__init__(); self.detail_calls = 0
        def match(self, match_id):
            self.detail_calls += 1
            return [{"id": match_id, "homeTeam": {"name": "USA"},
                     "awayTeam": {"name": "Paraguay"},
                     "state": {"description": "Finished", "clock": 90,
                               "score": {"current": "4 - 1"}}}]
    c = _C()
    svc = LiveDataService(c, _index())
    s = svc.match_summary(1267454654, now=0.0)
    assert s["home"] == "USA" and s["home_score"] == 4 and s["state"] == "finished"
    svc.match_summary(1267454654, now=5.0)        # cached
    assert c.detail_calls == 1


def test_match_summary_none_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.match_summary(1, now=0.0) is None


# ---------------------------------------------------------------------------
# update_player_stats / team_leaders
# ---------------------------------------------------------------------------

from src.data.live import player_store  # noqa: E402


class _StatsClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.event_calls = {}

    def events(self, match_id):
        self.event_calls[match_id] = self.event_calls.get(match_id, 0) + 1
        return [
            {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
             "playerId": 100, "assist": "C. Pulisic", "assistingPlayerId": 200},
            {"team": {"name": "USA"}, "type": "Yellow Card", "player": "T. Adams",
             "playerId": 300},
        ]


def test_update_player_stats_fetches_and_stores_finished(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_player_stats(matches, now=0.0)
    assert player_store.stored_match_states(path) == {1: MatchState.FINISHED.value}
    assert c.event_calls[1] == 1


def test_update_player_stats_skips_already_stored_finished(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_player_stats(matches, now=0.0)
    svc.update_player_stats(matches, now=1.0)   # second pass must not re-fetch
    assert c.event_calls[1] == 1


def test_update_player_stats_overwrites_live(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 2, "state": MatchState.LIVE.value}]
    svc.update_player_stats(matches, now=0.0)
    svc.update_player_stats(matches, now=1.0)   # live always re-fetched
    assert c.event_calls[2] == 2


def test_update_player_stats_noop_without_store():
    svc = LiveDataService(_StatsClient(), _index())   # no player_store
    svc.update_player_stats([{"match_id": 1, "state": "finished"}], now=0.0)  # no crash


def test_team_leaders_groups_and_ranks(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    # Two matches for USA so apps and sums accumulate.
    svc.update_player_stats([{"match_id": 1, "state": MatchState.FINISHED.value}], now=0.0)
    svc.update_player_stats([{"match_id": 2, "state": MatchState.FINISHED.value}], now=0.0)
    leaders = svc.team_leaders("USA")
    goals = leaders["goals"]
    assert goals[0]["player"] == "F. Balogun"
    assert goals[0]["value"] == 2          # one goal in each of two matches
    assert goals[0]["apps"] == 2
    assert leaders["assists"][0]["value"] == 2     # C. Pulisic, two assists
    cards = leaders["cards"][0]
    assert cards["value"] == 2                     # T. Adams, total cards
    assert cards["yellow"] == 2                     # two yellows across two matches
    assert cards["red"] == 0
    assert "rating" not in leaders                  # API exposes no per-player rating


def test_team_leaders_empty_without_store():
    svc = LiveDataService(_StatsClient(), _index())
    assert svc.team_leaders("USA") == {}
