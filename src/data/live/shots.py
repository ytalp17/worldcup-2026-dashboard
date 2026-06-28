"""Parse per-shot rows from the Highlightly match-detail endpoint
(homeTeam.shots[]/awayTeam.shots[]). Stage is assigned later at store-write
time (mirrors team_match_stats), so ShotRecord defaults stage='group'."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShotRecord:
    match_id: int
    team: str
    player: str
    time: str
    outcome: str
    goal_target: str | None
    opponent: str = ""
    stage: str = "group"


def _detail_obj(detail):
    if isinstance(detail, list):
        return detail[0] if detail else None
    return detail if isinstance(detail, dict) else None


def parse_shots(match_id: int, detail) -> list[ShotRecord]:
    obj = _detail_obj(detail)
    if not isinstance(obj, dict):
        return []
    # Both teams come from the same detail object, so each side's opponent is
    # simply the other side's name ("vs <team>" in the shot drawer).
    names = {side: str(t.get("name") or "") if isinstance(t := obj.get(side), dict)
             else "" for side in ("homeTeam", "awayTeam")}
    opponent = {"homeTeam": names["awayTeam"], "awayTeam": names["homeTeam"]}
    rows: list[ShotRecord] = []
    for side in ("homeTeam", "awayTeam"):
        team_obj = obj.get(side)
        if not isinstance(team_obj, dict):
            continue
        team = names[side]
        shots = team_obj.get("shots")
        if not isinstance(shots, list):
            continue
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            gt = shot.get("goalTarget")
            rows.append(ShotRecord(
                match_id=match_id,
                team=team,
                player=str(shot.get("playerName") or ""),
                time=str(shot.get("time") or ""),
                outcome=str(shot.get("outcome") or ""),
                goal_target=gt if gt is None else str(gt),
                opponent=opponent[side],
            ))
    return rows
