"""Derive a team's recent form (W/D/L) from finished tournament matches.

The live feed carries no per-team "form" string, so we reconstruct it from the
finished match dicts the snapshot/per-date caches expose (each with ``home``,
``away``, ``home_score``, ``away_score``, ``state`` and an ISO ``kickoff``).
Results are ordered chronologically by kickoff so the strip reads oldest →
newest, left to right.

Pure and offline: name matching is delegated to a ``normalize`` callable (the
app passes ``reconcile.canonical_team``) so the live feed's spellings line up
with the official team names, and the whole thing is unit-testable without the
API. Only WC-2026 fixtures reach here because the caller draws exclusively from
the tournament's per-date match snapshots.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

WIN = "W"
DRAW = "D"
LOSS = "L"


def match_result(team: str, match: dict,
                 normalize: Callable[[str], str]) -> str | None:
    """``"W"``/``"D"``/``"L"`` for ``team`` in a finished match, else ``None``.

    Returns ``None`` when the match is not finished, the score is missing, or
    ``team`` did not play in it. ``normalize`` maps both the queried team and
    the feed's home/away names to a common spelling before comparing.
    """
    if (match.get("state") or "").strip().lower() != "finished":
        return None
    home_score, away_score = match.get("home_score"), match.get("away_score")
    if home_score is None or away_score is None:
        return None

    target = normalize(team)
    if normalize(match.get("home", "")) == target:
        scored, conceded = home_score, away_score
    elif normalize(match.get("away", "")) == target:
        scored, conceded = away_score, home_score
    else:
        return None

    if scored > conceded:
        return WIN
    if scored < conceded:
        return LOSS
    return DRAW


def recent_form(team: str, matches: Iterable[dict],
                normalize: Callable[[str], str], limit: int = 5) -> list[str]:
    """Chronological W/D/L for ``team``'s finished matches (oldest → newest),
    keeping only the most recent ``limit``. Matches are ordered by their ISO
    ``kickoff`` string (ISO timestamps sort chronologically); unfinished and
    unrelated matches are skipped."""
    decided: list[tuple[str, str]] = []  # (kickoff, result)
    for match in matches:
        result = match_result(team, match, normalize)
        if result is not None:
            decided.append((match.get("kickoff") or "", result))
    decided.sort(key=lambda pair: pair[0])
    return [result for _kickoff, result in decided][-limit:]
