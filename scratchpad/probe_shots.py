"""One-off probe: inspect goalTarget / outcome values on shots across a
sample of finished WC2026 matches. Reads the API key from .env, reuses the
project's HighlightlyClient.
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/yberber/Documents/WC2026")
from src.data.live.client import HighlightlyClient, HighlightlyError, RateLimitError  # noqa: E402
from src.data.live.shots import parse_shots               # noqa: E402
from src.data.live.goal_mouth import aggregate_goal_mouth  # noqa: E402

LEAGUE_ID = 1635
SEASON = 2026
MAX_MATCHES = 20  # cap API spend


def load_key() -> str:
    for line in Path("/Users/yberber/Documents/WC2026/.env").read_text().splitlines():
        if line.startswith("HIGHLIGHTLY_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no HIGHLIGHTLY_API_KEY in .env")


def is_finished(m: dict) -> bool:
    # state shape is unknown here; check a few likely spots, defensively.
    state = m.get("state")
    if isinstance(state, dict):
        desc = (state.get("description") or "").lower()
        return "finished" in desc or state.get("clock") == 90 or "ended" in desc
    if isinstance(state, str):
        return "finish" in state.lower()
    return False


def collect_shots(team: dict) -> list[dict]:
    shots = team.get("shots") if isinstance(team, dict) else None
    return shots if isinstance(shots, list) else []


def main() -> None:
    client = HighlightlyClient(api_key=load_key())

    # WC2026 group stage: scan June 2026 dates for finished matches.
    dates = [f"2026-06-{d:02d}" for d in range(11, 27)]
    match_ids: list[int] = []
    seen: set[int] = set()
    for d in dates:
        if len(match_ids) >= MAX_MATCHES:
            break
        try:
            resp = client.matches(date=d, league_id=LEAGUE_ID)
        except (HighlightlyError, RateLimitError) as e:
            print(f"[matches {d}] {e}", file=sys.stderr)
            continue
        rows = resp.get("data") if isinstance(resp, dict) else resp
        rows = rows if isinstance(rows, list) else []
        finished = [m for m in rows if is_finished(m)]
        print(f"{d}: {len(rows)} matches, {len(finished)} finished")
        for m in finished:
            mid = m.get("id") or m.get("match_id")
            if mid and mid not in seen:
                seen.add(mid)
                match_ids.append(mid)
        time.sleep(0.2)

    match_ids = match_ids[:MAX_MATCHES]
    print(f"\nSampling {len(match_ids)} match detail calls...\n")

    goal_target = Counter()
    outcome = Counter()
    null_target_outcomes = Counter()
    total_shots = 0
    matches_with_shots = 0
    per_team = defaultdict(list)

    for mid in match_ids:
        try:
            detail = client.match(mid)
        except (HighlightlyError, RateLimitError) as e:
            print(f"[match {mid}] {e}", file=sys.stderr)
            continue
        obj = detail[0] if isinstance(detail, list) and detail else detail
        if not isinstance(obj, dict):
            continue
        match_shots = 0
        # Accumulate ShotRecords per team for cross-tab aggregation
        for rec in parse_shots(mid, detail):
            per_team[rec.team].append(rec)
            match_shots += 1
            oc = rec.outcome
            outcome[str(oc)] += 1
            if rec.goal_target is None:
                null_target_outcomes[str(oc)] += 1
            else:
                goal_target[str(rec.goal_target)] += 1
        total_shots += match_shots
        if match_shots:
            matches_with_shots += 1
        time.sleep(0.2)

    print("=" * 60)
    print(f"Matches sampled (detail fetched): {len(match_ids)}")
    print(f"Matches that had >=1 shot:        {matches_with_shots}")
    print(f"Total shots collected:            {total_shots}")
    print(f"requests_remaining (last header): {client.requests_remaining}")

    print("\n--- distinct non-null goalTarget values (count) ---")
    for v, c in goal_target.most_common():
        print(f"  {v!r:>12}: {c}")

    print("\n--- distinct outcome values (count) ---")
    for v, c in outcome.most_common():
        print(f"  {v!r:>14}: {c}")

    null_total = sum(null_target_outcomes.values())
    print(f"\n--- shots with goalTarget=null: {null_total} ---")
    for v, c in null_target_outcomes.most_common():
        print(f"  outcome {v!r:>14}: {c}")

    print("\n--- per-team zone x outcome / zone x shooter ---")
    for team, recs in sorted(per_team.items()):
        agg = aggregate_goal_mouth(recs)
        print(f"\n{team}: {agg['totals']}")
        for zid, z in agg["zones"].items():
            if z["count"]:
                print(f"  {zid:>16}: {z['count']:>3}  {z['outcomes']}")
                for s in z["shooters"][:3]:
                    print(f"      {s['time']:>6}  {s['player']}  {s['outcome']}")


if __name__ == "__main__":
    main()
