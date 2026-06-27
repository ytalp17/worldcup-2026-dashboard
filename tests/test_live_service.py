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


class _CountingStandingsClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.standings_calls = 0

    def standings(self, league_id, season):
        self.standings_calls += 1
        return super().standings(league_id, season)


def test_standings_shapes_and_caches_within_ttl():
    client = _CountingStandingsClient()
    svc = LiveDataService(client, _index())
    table = svc.standings(now=0.0)
    assert table["Group A"][0]["team"] == "Mexico"
    assert "Group Stage" not in table
    svc.standings(now=100.0)                 # within the 3600s TTL -> cached
    assert client.standings_calls == 1


def test_standings_force_bypasses_cache():
    client = _CountingStandingsClient()
    svc = LiveDataService(client, _index())
    svc.standings(now=0.0)
    assert client.standings_calls == 1
    svc.standings(now=5.0, force=True)       # force -> fresh API call despite TTL
    assert client.standings_calls == 2


def test_standings_empty_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.standings(now=0.0) == {}


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


# ---------------------------------------------------------------------------
# update_team_stats
# ---------------------------------------------------------------------------

from src.data.live import team_stats_store  # noqa: E402


class _TeamStatsClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.stat_calls = {}

    def statistics(self, match_id):
        self.stat_calls[match_id] = self.stat_calls.get(match_id, 0) + 1
        return [
            {"team": {"name": "USA"}, "statistics": [
                {"displayName": "Expected Goals", "value": 1.5},
                {"displayName": "Shots on target", "value": 4},
                {"displayName": "Possession", "value": 0.6},
                {"displayName": "Yellow cards", "value": 2}]},
            {"team": {"name": "Paraguay"}, "statistics": [
                {"displayName": "Expected Goals", "value": 0.7},
                {"displayName": "Possession", "value": 0.4}]},
        ]


def test_update_team_stats_fetches_and_stores_finished(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    svc.update_team_stats([{"match_id": 1, "state": MatchState.FINISHED.value}], now=0.0)
    assert team_stats_store.stored_match_states(path) == {1: MatchState.FINISHED.value}
    assert c.stat_calls[1] == 1
    loaded = team_stats_store.load(path)
    usa = next(r for r in loaded[1] if r.team == "USA")
    assert usa.stats["xg"] == 1.5


def test_update_team_stats_skips_already_stored_finished(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    m = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_team_stats(m, now=0.0)
    svc.update_team_stats(m, now=1.0)
    assert c.stat_calls[1] == 1


def test_update_team_stats_overwrites_live(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    m = [{"match_id": 2, "state": MatchState.LIVE.value}]
    svc.update_team_stats(m, now=0.0)
    svc.update_team_stats(m, now=1.0)
    assert c.stat_calls[2] == 2


def test_update_team_stats_noop_without_store():
    svc = LiveDataService(_TeamStatsClient(), _index())   # no team_store
    svc.update_team_stats([{"match_id": 1, "state": "finished"}], now=0.0)  # no crash


# ---------------------------------------------------------------------------
# tournament_player_leaders / tournament_team_leaders
# ---------------------------------------------------------------------------

from src.data.live.player_stats import PlayerMatchStat  # noqa: E402
from src.data.live.team_match_stats import TeamMatchStat, STAT_KEYS  # noqa: E402


def _pstat(mid, team, player, pid, goals=0, assists=0, yellow=0, red=0):
    return PlayerMatchStat(match_id=mid, team=team, player=player, player_id=pid,
                           goals=goals, assists=assists, yellow=yellow, red=red)


def _tstat(mid, team, **ov):
    stats = {k: 0.0 for k in STAT_KEYS}
    stats.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=stats)


def test_tournament_player_leaders_aggregates_all_teams(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=2, yellow=1),
                         _pstat(1, "Brazil", "Vinicius", 200, goals=1, assists=1)])
    player_store.upsert(path, 2, "finished",
                        [_pstat(2, "USA", "F. Balogun", 100, goals=1)])
    svc = LiveDataService(_FakeClient(), _index(), player_store=path)
    L = svc.tournament_player_leaders()
    goals = L["goals"]
    assert goals[0]["player"] == "F. Balogun"
    assert goals[0]["team"] == "USA"
    assert goals[0]["value"] == 3        # 2 + 1 across two matches
    assert goals[0]["apps"] == 2
    cards = L["cards"][0]
    assert cards["yellow"] == 1 and cards["red"] == 0


def test_tournament_player_leaders_empty_without_store():
    svc = LiveDataService(_FakeClient(), _index())
    assert svc.tournament_player_leaders() == {}


def test_tournament_team_leaders_sums_avgs_and_ratios(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_tstat(1, "USA", xg=1.5, shots_on=4, shots_off=6,
                                    passes_total=400, passes_succ=300, possession=0.6,
                                    yellow=1)])
    team_stats_store.upsert(path, 2, "finished",
                            [_tstat(2, "USA", xg=0.5, shots_on=2, shots_off=4,
                                    passes_total=600, passes_succ=480, possession=0.5,
                                    yellow=2)])
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    standings = {"Group A": [{"team": "USA", "goals_for": 5, "goals_against": 2,
                              "goal_diff": 3, "points": 6, "played": 2,
                              "won": 2, "drawn": 0, "lost": 0}]}
    T = svc.tournament_team_leaders(standings)
    atk = next(r for r in T["attack"] if r["team"] == "USA")
    assert atk["xg"] == 2.0                 # summed
    assert atk["shots"] == 16               # (4+6)+(2+4)
    assert atk["goals"] == 5                # from standings GF
    assert atk["apps"] == 2
    poss = next(r for r in T["possession"] if r["team"] == "USA")
    assert poss["possession"] == 55.0       # mean(0.6,0.5)*100
    assert poss["pass_acc"] == 78.0         # 780/1000 *100
    disc = next(r for r in T["discipline"] if r["team"] == "USA")
    assert disc["yellow"] == 3


def test_tournament_team_leaders_empty_without_store():
    svc = LiveDataService(_FakeClient(), _index())
    assert svc.tournament_team_leaders() == {}


def test_tournament_team_leaders_goals_default_zero_without_standings(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_tstat(1, "USA", xg=1.0)])
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    T = svc.tournament_team_leaders()        # no standings passed
    atk = next(r for r in T["attack"] if r["team"] == "USA")
    assert atk["goals"] == 0                  # GF join absent -> 0


def test_tournament_team_leaders_shot_acc_zero_when_no_shots(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_tstat(1, "USA", corners=3)])
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    atk = next(r for r in svc.tournament_team_leaders()["attack"] if r["team"] == "USA")
    assert atk["shots"] == 0
    assert atk["shot_acc"] == 0.0             # no division-by-zero


def test_tournament_player_leaders_group_only_excludes_knockout(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=2)],
                        stage="group")
    player_store.upsert(path, 2, "finished",
                        [_pstat(2, "USA", "F. Balogun", 100, goals=5)],
                        stage="knockout")
    svc = LiveDataService(_FakeClient(), _index(), player_store=path)
    all_goals = svc.tournament_player_leaders()["goals"][0]
    grp_goals = svc.tournament_player_leaders(group_only=True)["goals"][0]
    assert all_goals["value"] == 7      # 2 + 5 across both stages
    assert grp_goals["value"] == 2      # group stage only
    assert grp_goals["apps"] == 1


def test_tournament_team_leaders_group_only_excludes_knockout(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_tstat(1, "USA", shots_on=4)], stage="group")
    team_stats_store.upsert(path, 2, "finished",
                            [_tstat(2, "USA", shots_on=10)], stage="knockout")
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    all_atk = next(r for r in svc.tournament_team_leaders()["attack"]
                   if r["team"] == "USA")
    grp_atk = next(r for r in
                   svc.tournament_team_leaders(group_only=True)["attack"]
                   if r["team"] == "USA")
    assert all_atk["shots"] == 14       # 4 + 10
    assert grp_atk["shots"] == 4        # group stage only
    assert grp_atk["apps"] == 1


# ---------------------------------------------------------------------------
# stage tagging at write time (Task 5)
# ---------------------------------------------------------------------------

from datetime import timezone  # noqa: E402

_KO_START = datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc)


def _match(mid, kickoff):
    return {"match_id": mid, "state": MatchState.FINISHED.value, "kickoff": kickoff,
            "home": "USA", "away": "Brazil"}


def test_update_player_stats_tags_stage_from_kickoff(tmp_path):
    path = tmp_path / "ps.csv"
    client = _StatsClient()   # returns event rows for any match_id
    svc = LiveDataService(client, _index(), player_store=path,
                          knockout_start=_KO_START)
    svc.update_player_stats([_match(1, "2026-06-20T19:00:00+00:00"),
                             _match(2, "2026-06-29T19:00:00+00:00")], 0.0)
    loaded = player_store.load(path)
    assert loaded[1][0].stage == "group"
    assert loaded[2][0].stage == "knockout"


def test_update_team_stats_tags_stage_from_kickoff(tmp_path):
    path = tmp_path / "ts.csv"
    client = _TeamStatsClient()   # returns stat rows for any match_id
    svc = LiveDataService(client, _index(), team_store=path,
                          knockout_start=_KO_START)
    svc.update_team_stats([_match(1, "2026-06-20T19:00:00+00:00"),
                           _match(2, "2026-06-29T19:00:00+00:00")], 0.0)
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stage == "group"
    assert loaded[2][0].stage == "knockout"
