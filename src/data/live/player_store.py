from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.player_stats import PlayerMatchStat

# A gitignored cache of per-match player stats. `state` records the match state
# at write time so the updater can skip finished matches already on disk.
FIELDS = ["match_id", "team", "player", "player_id",
          "goals", "assists", "yellow", "red", "state"]


def load(path) -> dict[int, list[PlayerMatchStat]]:
    """match_id -> list[PlayerMatchStat]. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[PlayerMatchStat]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            out.setdefault(mid, []).append(PlayerMatchStat(
                match_id=mid,
                team=row["team"],
                player=row["player"],
                player_id=int(row["player_id"]) if row["player_id"] else None,
                goals=int(row["goals"]),
                assists=int(row["assists"]),
                yellow=int(row["yellow"]),
                red=int(row["red"]),
            ))
    return out


def stored_match_states(path) -> dict[int, str]:
    """match_id -> last stored state. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["match_id"])] = row["state"]
    return out


def upsert(path, match_id: int, state: str, rows) -> None:
    """Atomically replace all rows for `match_id` with `rows` (tagged `state`)."""
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
            w.writerow({k: r.get(k, "") for k in FIELDS})
        for s in rows:
            w.writerow({
                "match_id": s.match_id, "team": s.team, "player": s.player,
                "player_id": s.player_id if s.player_id is not None else "",
                "goals": s.goals, "assists": s.assists,
                "yellow": s.yellow, "red": s.red,
                "state": state,
            })
    os.replace(tmp, p)
