from __future__ import annotations

import logging

from src.data.live import models
from src.data.live.reconcile import find_stadium

logger = logging.getLogger(__name__)

LEAGUE_ID = 1635
SEASON = 2026
_MATCHES_TTL = 60.0
_STANDINGS_TTL = 3600.0


class LiveDataService:
    """Caches Highlightly responses and builds a JSON-serializable snapshot.

    Any failure while fetching or shaping a snapshot — a network/quota error
    from the client OR a parsing/programming error — is caught and logged, and
    the snapshot is marked ok=False (carrying the last good payload if there is
    one, else empty) so UI callbacks fall back to static data instead of
    crashing. The broad catch is deliberate (the live feed must never take the
    dashboard down); the logging keeps those failures visible for diagnosis.
    """

    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON):
        self._client = client
        self._stadium_index = stadium_index
        self._league_id = league_id
        self._season = season
        self._cache: dict[str, tuple[float, object]] = {}
        self._last_good: dict | None = None

    def _cached(self, key, ttl, now, fetch):
        hit = self._cache.get(key)
        if hit and (now - hit[0]) < ttl:
            return hit[1]
        value = fetch()
        self._cache[key] = (now, value)
        return value

    def snapshot(self, date: str, now: float) -> dict:
        try:
            raw_matches = self._cached(
                "matches", _MATCHES_TTL, now,
                lambda: self._client.matches(date=date, league_id=self._league_id))
            raw_standings = self._cached(
                "standings", _STANDINGS_TTL, now,
                lambda: self._client.standings(league_id=self._league_id, season=self._season))
            matches = models.parse_matches(raw_matches)
            payload = {
                "ok": True,
                "any_live": any(m.is_live for m in matches),
                "matches": [self._match_dict(m) for m in matches],
                "standings": {
                    name: [vars(s) for s in table]
                    for name, table in models.parse_standings(raw_standings).items()
                },
            }
            self._last_good = payload
            return payload
        except Exception:
            logger.exception("Live snapshot failed; falling back to static")
            if self._last_good is not None:
                return {**self._last_good, "ok": False}
            return {"ok": False, "any_live": False, "matches": [], "standings": {}}

    def _match_dict(self, m: models.LiveMatch) -> dict:
        return {
            "match_id": m.match_id,
            "home": m.home,
            "away": m.away,
            "venue": find_stadium(m.home, m.away, self._stadium_index),
            "state": m.state.value,
            "clock": m.clock,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "is_live": m.is_live,
        }


def next_delay(snapshot: dict) -> int:
    """Adaptive poll cadence (seconds): fast while any match is live, slow when idle."""
    return 60 if snapshot.get("any_live") else 1800
