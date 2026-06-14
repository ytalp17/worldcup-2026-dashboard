from __future__ import annotations

from dataclasses import dataclass

from src.data.live.reconcile import normalize

# Only these exact event types count as a goal for the scorer. "Own Goal" is
# deliberately excluded (not credited to the scorer); "VAR Goal Cancelled - ..."
# and other types are ignored.
_GOAL_TYPES = {"Goal", "Penalty"}


@dataclass(frozen=True)
class PlayerMatchStat:
    match_id: int
    team: str
    player: str
    player_id: int | None
    goals: int
    assists: int
    yellow: int
    red: int


def _team_name(raw) -> str:
    team = raw.get("team")
    if isinstance(team, dict):
        return team.get("name", "")
    return str(team or "")


def parse_player_stats(match_id: int, events) -> list[PlayerMatchStat]:
    """One row per player who appears in this match's events.

    Events drive goals/assists/cards, keyed by playerId when present, else
    normalized name. (The API exposes no per-player rating, so there is no
    topPlayers/detail source here — events are the only per-player data.)
    """
    agg: dict = {}

    def slot(team: str, player: str, pid) -> dict:
        key = pid if pid is not None else normalize(player)
        cur = agg.get(key)
        if cur is None:
            cur = {"team": team, "player": player, "player_id": pid,
                   "goals": 0, "assists": 0, "yellow": 0, "red": 0}
            agg[key] = cur
        return cur

    for e in (events or []):
        etype = str(e.get("type", ""))
        team = _team_name(e)
        player = str(e.get("player", ""))
        pid = e.get("playerId")
        if etype in _GOAL_TYPES:
            slot(team, player, pid)["goals"] += 1
            aname = e.get("assist")
            if aname:
                slot(team, str(aname), e.get("assistingPlayerId"))["assists"] += 1
        elif etype == "Yellow Card":
            slot(team, player, pid)["yellow"] += 1
        elif etype == "Red Card":
            slot(team, player, pid)["red"] += 1
        elif etype == "Own Goal":
            slot(team, player, pid)   # scorer row exists but is NOT credited a goal

    return [PlayerMatchStat(match_id=match_id, **v) for v in agg.values()]
