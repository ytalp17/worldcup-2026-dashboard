from __future__ import annotations

from src.data.live.player_stats import PlayerMatchStat, parse_player_stats

EVENTS = [
    {"team": {"name": "USA"}, "type": "Own Goal", "player": "D. Bobadilla",
     "playerId": 31412381, "assist": None, "assistingPlayerId": None},
    {"team": {"name": "Paraguay"}, "type": "Yellow Card", "player": "J. Caceres",
     "playerId": 31554866, "assist": None, "assistingPlayerId": None},
    {"team": {"name": "USA"}, "type": "VAR Goal Cancelled - Offside",
     "player": "F. Balogun", "playerId": 22352589, "assist": None,
     "assistingPlayerId": None},
    {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
     "playerId": 22352589, "assist": "C. Pulisic", "assistingPlayerId": 2891},
    {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
     "playerId": 22352589, "assist": "M. Tillman", "assistingPlayerId": 26088111},
    {"team": {"name": "USA"}, "type": "Red Card", "player": "T. Adams",
     "playerId": 999, "assist": None, "assistingPlayerId": None},
]


def _by_player(rows):
    return {r.player: r for r in rows}


def test_goals_count_excludes_own_goal_and_cancelled():
    rows = parse_player_stats(7, EVENTS)
    balogun = next(r for r in rows if r.player_id == 22352589)
    assert balogun.goals == 2          # two Goal events; VAR-cancelled not counted
    bob = next(r for r in rows if r.player_id == 31412381)
    assert bob.goals == 0              # Own Goal not credited to scorer


def test_assists_tallied_to_assisting_player():
    rows = parse_player_stats(7, EVENTS)
    by_id = {r.player_id: r for r in rows}
    assert by_id[2891].assists == 1            # C. Pulisic
    assert by_id[26088111].assists == 1        # M. Tillman


def test_cards_tallied():
    rows = parse_player_stats(7, EVENTS)
    by_id = {r.player_id: r for r in rows}
    assert by_id[31554866].yellow == 1
    assert by_id[999].red == 1


def test_returns_player_match_stat_with_match_id():
    rows = parse_player_stats(7, EVENTS)
    assert rows and all(isinstance(r, PlayerMatchStat) for r in rows)
    assert all(r.match_id == 7 for r in rows)


def test_handles_empty_inputs():
    assert parse_player_stats(7, []) == []
    assert parse_player_stats(7, None) == []
