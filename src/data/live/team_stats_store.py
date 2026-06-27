from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat

# A gitignored cache of per-match team statistics. `state` records the match
# state at write time so the updater can skip finished matches already on disk.
FIELDS = ["match_id", "team", "state", "stage"] + STAT_KEYS


def load(path) -> dict[int, list[TeamMatchStat]]:
    """match_id -> list[TeamMatchStat]. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[TeamMatchStat]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            stats = {k: float(row[k]) if row.get(k) else 0.0 for k in STAT_KEYS}
            out.setdefault(mid, []).append(
                TeamMatchStat(match_id=mid, team=row["team"], stats=stats,
                              stage=row.get("stage") or "group"))
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
            base = {"match_id": s.match_id, "team": s.team, "state": state,
                    "stage": stage}
            base.update({k: s.stats.get(k, 0.0) for k in STAT_KEYS})
            w.writerow(base)
    os.replace(tmp, p)
