"""Gitignored per-match shot cache (mirrors team_stats_store). `state` records
the match state at write time so the updater can skip finished-and-stored
matches; `stage` tags group vs knockout for the group-only filter."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.shots import ShotRecord

FIELDS = ["match_id", "team", "state", "stage",
          "player", "time", "outcome", "goal_target"]


def load(path) -> dict[int, list[ShotRecord]]:
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[ShotRecord]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            gt = row.get("goal_target")
            out.setdefault(mid, []).append(ShotRecord(
                match_id=mid, team=row["team"], player=row.get("player", ""),
                time=row.get("time", ""), outcome=row.get("outcome", ""),
                goal_target=(gt if gt else None),
                stage=row.get("stage") or "group"))
    return out


def stored_match_states(path) -> dict[int, str]:
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["match_id"])] = row["state"]
    return out


def upsert(path, match_id: int, state: str, rows, stage: str = "group") -> None:
    """Atomically replace all rows for `match_id` with `rows` (tagged `state`
    and `stage`)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    kept = []
    if p.exists():
        with p.open(newline="") as f:
            kept = [r for r in csv.DictReader(f) if int(r["match_id"]) != match_id]
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in kept:
            out_row = {k: r.get(k, "") for k in FIELDS}
            out_row["stage"] = r.get("stage") or "group"
            w.writerow(out_row)
        for s in rows:
            w.writerow({
                "match_id": s.match_id, "team": s.team, "state": state,
                "stage": stage, "player": s.player, "time": s.time,
                "outcome": s.outcome,
                "goal_target": "" if s.goal_target is None else s.goal_target,
            })
    os.replace(tmp, p)
