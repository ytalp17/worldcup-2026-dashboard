from __future__ import annotations

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
}


def normalize(name: str) -> str:
    """Lowercase and collapse internal whitespace for stable matching."""
    return " ".join((name or "").strip().lower().split())


def canonical_team(name: str, aliases: dict[str, str] = TEAM_ALIASES) -> str:
    """Normalized team name, mapped through the alias table when needed."""
    norm = normalize(name)
    return aliases.get(norm, norm)


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
