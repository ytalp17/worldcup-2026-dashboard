from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

_HALF_TIME = {"halftime", "half time", "ht", "break"}
_FINISHED = ("finished", "full time", "ft", "after extra", "after penalt", "ended")
_SCHEDULED = {"not started", "scheduled", "ns", "tbd", ""}


class MatchState(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALF_TIME = "half_time"
    FINISHED = "finished"
    OTHER = "other"


def _classify(description: str | None) -> MatchState:
    text = (description or "").strip().lower()
    if text in _SCHEDULED:
        return MatchState.SCHEDULED
    if text in _HALF_TIME:
        return MatchState.HALF_TIME
    if any(token in text for token in _FINISHED):
        return MatchState.FINISHED
    if any(token in text for token in ("half", "extra", "penal", "live", "progress")):
        return MatchState.LIVE
    return MatchState.OTHER


def _split_score(current: str | None) -> tuple[int | None, int | None]:
    if not current or "-" not in current:
        return None, None
    home, _, away = current.partition("-")
    try:
        return int(home.strip()), int(away.strip())
    except ValueError:
        return None, None


@dataclass(frozen=True)
class LiveMatch:
    match_id: int
    home: str
    away: str
    state: MatchState
    clock: int | None
    home_score: int | None
    away_score: int | None

    @property
    def is_live(self) -> bool:
        return self.state in (MatchState.LIVE, MatchState.HALF_TIME)


@dataclass(frozen=True)
class MatchEvent:
    minute: int
    type: str
    player: str
    team: str


@dataclass(frozen=True)
class Standing:
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goal_diff: int
    points: int


def parse_match(raw: dict) -> LiveMatch:
    state = raw.get("state") or {}
    score = (state.get("score") or {}).get("current")
    home_score, away_score = _split_score(score)
    return LiveMatch(
        match_id=int(raw["id"]),
        home=(raw.get("homeTeam") or {}).get("name", ""),
        away=(raw.get("awayTeam") or {}).get("name", ""),
        state=_classify(state.get("description")),
        clock=state.get("clock"),
        home_score=home_score,
        away_score=away_score,
    )


def parse_matches(raw: dict) -> list[LiveMatch]:
    return [parse_match(m) for m in raw.get("data", [])]


def parse_events(raw: list) -> list[MatchEvent]:
    events = [
        MatchEvent(
            minute=int(e.get("minute", 0)),
            type=str(e.get("type", "")),
            player=str(e.get("player", "")),
            team=str(e.get("team", "")),
        )
        for e in (raw or [])
    ]
    return sorted(events, key=lambda e: e.minute)


def parse_standings(raw: dict) -> dict[str, list[Standing]]:
    table: dict[str, list[Standing]] = {}
    for group in raw.get("groups", []):
        name = group.get("name", "")
        if name == "Group Stage":   # rollup, not a real group
            continue
        rows = []
        for s in group.get("standings", []):
            total = s.get("total") or {}
            rows.append(Standing(
                team=(s.get("team") or {}).get("name", ""),
                played=int(total.get("games", 0)),
                won=int(total.get("wins", 0)),
                drawn=int(total.get("draws", 0)),
                lost=int(total.get("loses", 0)),
                goal_diff=int(total.get("scoredGoals", 0)) - int(total.get("receivedGoals", 0)),
                points=int(s.get("points", 0)),
            ))
        table[name] = rows
    return table
