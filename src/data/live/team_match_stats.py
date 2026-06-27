from __future__ import annotations

from dataclasses import dataclass

# Persisted team-stat keys (ordered) and the API displayName each maps from.
# Low-value fields (Attacks, Free Kicks, Throw-Ins, ...) are intentionally omitted.
_DISPLAY_TO_KEY = {
    "Expected Goals": "xg",
    "Expected Assists": "xa",
    "Big Chances Created": "big_chances",
    "Possession": "possession",
    "Shots on target": "shots_on",
    "Shots off target": "shots_off",
    "Blocked shots": "shots_blocked",
    "Shots within penalty area": "shots_in_box",
    "Corners": "corners",
    "Total passes": "passes_total",
    "Successful passes": "passes_succ",
    "Key Passes": "key_passes",
    "Passes Into Final Third": "passes_final_third",
    "Long Passes": "long_passes",
    "Crosses": "crosses",
    "Successful Crosses": "crosses_succ",
    "Dribbles": "dribbles",
    "Successful Dribbles": "dribbles_succ",
    "Tackles": "tackles",
    "Successful Tackles": "tackles_succ",
    "Interceptions": "interceptions",
    "Clearances": "clearances",
    "Aerial Duels": "aerials",
    "Successful Aerial Duels": "aerials_won",
    "Goalkeeper saves": "gk_saves",
    "Fouls": "fouls",
    "Offsides": "offsides",
    "Yellow cards": "yellow",
    "Red cards": "red",
}

STAT_KEYS = list(_DISPLAY_TO_KEY.values())


@dataclass(frozen=True)
class TeamMatchStat:
    match_id: int
    team: str
    stats: dict   # every key in STAT_KEYS -> float (missing -> 0.0)
    stage: str = "group"


def parse_team_match_stats(match_id: int, statistics) -> list[TeamMatchStat]:
    """One TeamMatchStat per team from a parsed statistics dict
    ({team: {displayName: value}}). Unknown displayNames are ignored; any
    persisted key absent from the API defaults to 0.0."""
    out = []
    for team, sd in (statistics or {}).items():
        vals = {k: 0.0 for k in STAT_KEYS}
        for disp, value in (sd or {}).items():
            key = _DISPLAY_TO_KEY.get(disp)
            if key is None or value is None:
                continue
            try:
                vals[key] = float(value)
            except (TypeError, ValueError):
                pass
        out.append(TeamMatchStat(match_id=match_id, team=team, stats=vals))
    return out
