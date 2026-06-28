"""Pure per-team aggregation of shot records into the goal-mouth structure.
Shared by LiveDataService.team_goal_mouth and the probe script."""
from __future__ import annotations

from src.data.live.goal_mouth_zones import (
    ON_TARGET, classify_target, parse_shot_minute,
)


def _bump(bucket: dict, outcome: str) -> None:
    bucket["count"] += 1
    bucket["outcomes"][outcome] = bucket["outcomes"].get(outcome, 0) + 1


def aggregate_goal_mouth(records, group_only: bool = False) -> dict:
    recs = [r for r in records
            if not (group_only and getattr(r, "stage", "group") != "group")]

    zones = {z: {"count": 0, "outcomes": {}, "shooters": []} for z in ON_TARGET}
    margins: dict[str, dict] = {}
    off = {"count": 0, "outcomes": {}}
    other = {"count": 0, "outcomes": {}}
    woodwork = 0

    for r in recs:
        if r.outcome == "Post":
            woodwork += 1  # Woodwork is an overlay tally; Post shots are also counted in their zone.
        region = classify_target(r.goal_target)
        if region == "off_target":
            _bump(off, r.outcome)
            continue
        if region == "other":
            _bump(other, r.outcome)
            continue
        if region in zones:
            bucket = zones[region]
        else:  # a near-miss margin — created on first occurrence only
            bucket = margins.setdefault(region,
                                        {"count": 0, "outcomes": {}, "shooters": []})
        _bump(bucket, r.outcome)
        bucket["shooters"].append(
            {"time": r.time, "player": r.player, "outcome": r.outcome,
             "opponent": getattr(r, "opponent", "")})

    for bucket in list(zones.values()) + list(margins.values()):
        bucket["shooters"].sort(key=lambda s: parse_shot_minute(s["time"]))

    on_target = sum(zones[z]["count"] for z in ON_TARGET)
    near_miss = sum(m["count"] for m in margins.values())
    return {
        "zones": {**zones, **margins},
        "off_target": off,
        "other": other,
        "totals": {
            "on_target": on_target, "near_miss": near_miss, "woodwork": woodwork,
            "off_target": off["count"], "other": other["count"], "total": len(recs),
        },
    }
