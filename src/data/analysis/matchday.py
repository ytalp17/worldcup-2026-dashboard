from __future__ import annotations

from src.data.live.models import MatchState
from src.data.live.reconcile import canonical_team

FINISHED = MatchState.FINISHED.value  # "finished"

# Re-exported so tests/callers canonicalize names the same way the joins do.
canonical = canonical_team


def finished_ids(states: dict[int, str]) -> set[int]:
    """match_ids whose last stored state is FINISHED."""
    return {mid for mid, st in (states or {}).items() if st == FINISHED}


def _fixture_index(matches) -> dict[frozenset, dict]:
    """{frozenset(canonical home, canonical away): {date, group}} for group-stage
    fixtures. Knockout rows (no group) are skipped."""
    out: dict[frozenset, dict] = {}
    for m in matches:
        if m.stage != "Group Stage" or not m.group:
            continue
        key = frozenset({canonical(m.home), canonical(m.away)})
        out[key] = {"date": m.date, "group": m.group}
    return out


def match_meta(stats_by_match: dict, matches) -> dict[int, dict]:
    """Map each stored match_id to its canonical team pair, fixture date, and
    group, by pairing the match's two stored team rows against the fixtures.

    A match with only one stored team row, or no matching fixture, still gets an
    entry with date/group = None so callers degrade rather than crash.
    """
    index = _fixture_index(matches)
    meta: dict[int, dict] = {}
    for mid, rows in (stats_by_match or {}).items():
        teams = tuple(canonical(r.team) for r in rows)
        info = index.get(frozenset(teams)) if len(set(teams)) == 2 else None
        meta[mid] = {
            "teams": teams,
            "date": info["date"] if info else None,
            "group": info["group"] if info else None,
        }
    return meta


def team_finished_matches(team_canon: str, finished: set[int],
                          meta: dict) -> list[int]:
    """A team's FINISHED match_ids in chronological order (date asc, then
    match_id). Matches with an unknown date sort last but keep stable order."""
    mine = [mid for mid in finished
            if team_canon in meta.get(mid, {}).get("teams", ())]
    far = max((m["date"] for m in meta.values() if m.get("date")), default=None)

    def key(mid):
        d = meta[mid].get("date")
        # None dates -> sort after all known dates, tie-break by id
        return (0, d, mid) if d is not None else (1, far, mid)

    return sorted(mine, key=key)
