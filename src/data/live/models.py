from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    kickoff: datetime | None = None  # scheduled kickoff (UTC), when known

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
    goals_for: int = 0
    goals_against: int = 0


def _parse_kickoff(raw: dict) -> datetime | None:
    value = raw.get("date")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


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
        kickoff=_parse_kickoff(raw),
    )


def parse_matches(raw: dict) -> list[LiveMatch]:
    return [parse_match(m) for m in raw.get("data", [])]


def _parse_minute(e: dict) -> int:
    """Extract a minute integer from an event dict.

    Handles both schemas:
    - New real API: ``time`` is a string like ``"7"`` or ``"45+5"`` (base only).
    - Old/inline test schema: ``minute`` is an integer.
    """
    raw_time = e.get("time")
    if raw_time is not None:
        # Strip stoppage-time suffix ("45+5" → "45")
        base = str(raw_time).split("+")[0]
        try:
            return int(base)
        except ValueError:
            pass
    return int(e.get("minute") or 0)


def parse_events(raw: list) -> list[MatchEvent]:
    events = [
        MatchEvent(
            minute=_parse_minute(e),
            type=str(e.get("type", "")),
            player=str(e.get("player", "")),
            team=(e.get("team") or {}).get("name", "") if isinstance(e.get("team"), dict) else str(e.get("team", "")),
        )
        for e in (raw or [])
    ]
    return sorted(events, key=lambda e: e.minute)


def parse_statistics(raw: list) -> dict:
    """Parse a list of two team-statistics objects into {team_name: {displayName: value}}."""
    return {
        (t.get("team") or {}).get("name", ""): {
            s["displayName"]: s["value"]
            for s in t.get("statistics", [])
        }
        for t in (raw or [])
    }


def parse_lineups(raw: dict) -> dict:
    """Parse homeTeam/awayTeam lineup data into {home/away: {formation, starters, subs}}."""
    def _team(data: dict) -> dict:
        if not data:
            return {"formation": "", "starters": [], "subs": [], "rows": []}
        # initialLineup is grouped by formation line (GK -> forwards); keep that
        # grouping in `rows` for the pitch, and flatten it into `starters`.
        rows = [
            [
                {"name": p["name"], "number": p["number"], "position": p["position"]}
                for p in row
            ]
            for row in data.get("initialLineup", [])
        ]
        starters = [p for row in rows for p in row]
        subs = [
            {"name": p["name"], "number": p["number"], "position": p["position"]}
            for p in data.get("substitutes", [])
        ]
        return {
            "formation": data.get("formation", ""),
            "starters": starters,
            "subs": subs,
            "rows": rows,
        }

    return {
        "home": _team((raw or {}).get("homeTeam") or {}),
        "away": _team((raw or {}).get("awayTeam") or {}),
    }


def parse_standings(raw: dict) -> dict[str, list[Standing]]:
    table: dict[str, list[Standing]] = {}
    for group in raw.get("groups", []):
        name = group.get("name", "")
        if name == "Group Stage":   # rollup, not a real group
            continue
        rows = []
        for s in group.get("standings", []):
            total = s.get("total") or {}
            scored = int(total.get("scoredGoals", 0))
            received = int(total.get("receivedGoals", 0))
            rows.append(Standing(
                team=(s.get("team") or {}).get("name", ""),
                played=int(total.get("games", 0)),
                won=int(total.get("wins", 0)),
                drawn=int(total.get("draws", 0)),
                lost=int(total.get("loses", 0)),
                goal_diff=scored - received,
                points=int(s.get("points", 0)),
                goals_for=scored,
                goals_against=received,
            ))
        table[name] = rows
    return table
