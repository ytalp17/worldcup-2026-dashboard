from __future__ import annotations

from datetime import datetime

# Map a normalized LIVE (Highlightly) team name to a normalized STATIC
# (our schedule) name, for the FIFA spelling differences. Seeded with the
# likely diffs; extend as live names are observed. Exact-matching names
# (Brazil, USA, Mexico, ...) need no entry.
TEAM_ALIASES = {
    "turkey": "türkiye",
    "south korea": "korea republic",
    "korea": "korea republic",
    "iran": "ir iran",
    "ivory coast": "côte d'ivoire",
    "dr congo": "congo dr",
    "cape verde": "cabo verde",
    "czech republic": "czechia",
    "bosnia & herzegovina": "bosnia and herzegovina",
}


def normalize(name: str) -> str:
    """Lowercase and collapse internal whitespace for stable matching."""
    return " ".join((name or "").strip().lower().split())


def canonical_team(name: str, aliases: dict[str, str] = TEAM_ALIASES) -> str:
    """Normalized team name, mapped through the alias table when needed."""
    norm = normalize(name)
    return aliases.get(norm, norm)


def index_matches_by_pair(api_matches, aliases: dict[str, str] = TEAM_ALIASES) -> dict[tuple[str, str], int]:
    """{(canonical_home, canonical_away): match_id} for API match dicts, so a
    static schedule match can be resolved to its API id by team pair."""
    return {
        (canonical_team(m["home"], aliases), canonical_team(m["away"], aliases)): m["match_id"]
        for m in api_matches
        if m.get("home") and m.get("away") and m.get("match_id") is not None
    }


def build_stadium_index(matches) -> dict[tuple[str, str], str]:
    """(canonical_home, canonical_away) -> stadium, from the static schedule."""
    return {
        (canonical_team(m.home), canonical_team(m.away)): m.stadium
        for m in matches
    }


def find_stadium(home: str, away: str, index: dict[tuple[str, str], str],
                 aliases: dict[str, str] = TEAM_ALIASES) -> str | None:
    """Stadium for a live match's team pair, or None if no static match.

    None is the graceful path: the match still shows in the strip/modal, it
    just gets no map marker badge.
    """
    key = (canonical_team(home, aliases), canonical_team(away, aliases))
    return index.get(key)


def _as_dt(value):
    """Coerce a datetime / ISO-8601 string / None to a datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def classify_stage(kickoff, knockout_start) -> str:
    """'knockout' if kickoff is at/after the knockout cutoff, else 'group'.

    Missing kickoff, unparseable kickoff, or missing cutoff all fall back to
    'group' — the safe default that never hides a match from Group-Stage view.
    """
    if knockout_start is None:
        return "group"
    ko = _as_dt(kickoff)
    if ko is None:
        return "group"
    if ko.tzinfo is None:
        return "group"
    return "knockout" if ko >= knockout_start else "group"
