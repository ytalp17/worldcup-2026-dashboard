from __future__ import annotations

import logging

from pathlib import Path

from src.data.live import models, player_store
from src.data.live.player_stats import parse_player_stats
from src.data.live.reconcile import canonical_team, find_stadium

logger = logging.getLogger(__name__)

LEAGUE_ID = 1635
SEASON = 2026
_MATCHES_TTL = 60.0
_STANDINGS_TTL = 3600.0
_MATCHES_ON_TTL = 600.0


class LiveDataService:
    """Caches Highlightly responses and builds a JSON-serializable snapshot.

    Any failure while fetching or shaping a snapshot — a network/quota error
    from the client OR a parsing/programming error — is caught and logged, and
    the snapshot is marked ok=False (carrying the last good payload if there is
    one, else empty) so UI callbacks fall back to static data instead of
    crashing. The broad catch is deliberate (the live feed must never take the
    dashboard down); the logging keeps those failures visible for diagnosis.
    """

    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON,
                 player_store=None):
        self._client = client
        self._stadium_index = stadium_index
        self._league_id = league_id
        self._season = season
        self._player_store = Path(player_store) if player_store else None
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

    def match_events(self, match_id: int, now: float) -> list[dict]:
        """On-demand events for one match (parsed dicts), cached like matches.
        Empty list on any failure so the modal still renders."""
        try:
            raw = self._cached(
                f"events:{match_id}", _MATCHES_TTL, now,
                lambda: self._client.events(match_id),
            )
            return [vars(e) for e in models.parse_events(raw)]
        except Exception:
            logger.exception("Live events fetch failed for match %s", match_id)
            return []

    def match_statistics(self, match_id: int, now: float) -> dict:
        """On-demand statistics for one match, cached like matches.
        Empty dict on any failure."""
        try:
            raw = self._cached(
                f"stats:{match_id}", _MATCHES_TTL, now,
                lambda: self._client.statistics(match_id),
            )
            return models.parse_statistics(raw)
        except Exception:
            logger.exception("Live statistics fetch failed for match %s", match_id)
            return {}

    def match_lineups(self, match_id: int, now: float) -> dict:
        """On-demand lineups for one match, cached like matches.
        Empty dict on any failure."""
        try:
            raw = self._cached(
                f"lineups:{match_id}", _MATCHES_TTL, now,
                lambda: self._client.lineups(match_id),
            )
            return models.parse_lineups(raw)
        except Exception:
            logger.exception("Live lineups fetch failed for match %s", match_id)
            return {}

    def matches_on(self, date_iso: str, now: float) -> list[dict]:
        """Match dicts for one calendar day (same shape as snapshot 'matches').
        Cached per date; [] on error."""
        try:
            raw = self._cached(
                f"matches:{date_iso}", _MATCHES_ON_TTL, now,
                lambda: self._client.matches(date=date_iso, league_id=self._league_id))
            return [self._match_dict(m) for m in models.parse_matches(raw)]
        except Exception:
            logger.exception("Live matches_on fetch failed for %s", date_iso)
            return []

    def match_summary(self, match_id: int, now: float) -> dict | None:
        """One match's header dict from the detail endpoint (bare list of one).
        Cached; None on error."""
        try:
            raw = self._cached(
                f"summary:{match_id}", _MATCHES_ON_TTL, now,
                lambda: self._client.match(match_id))
            rows = raw if isinstance(raw, list) else [raw]
            if not rows:
                return None
            return self._match_dict(models.parse_match(rows[0]))
        except Exception:
            logger.exception("Live match_summary fetch failed for %s", match_id)
            return None

    def update_player_stats(self, matches, now: float) -> None:
        """Refresh the player-stats cache from today's matches.

        Finished & already stored -> skip (no fetch). Finished & new, or live ->
        fetch events + detail once and overwrite that match's rows. Each match is
        independent: a failure is logged and skipped, leaving the cache intact.
        """
        if self._player_store is None:
            return
        stored = player_store.stored_match_states(self._player_store)
        live_states = {models.MatchState.LIVE.value, models.MatchState.HALF_TIME.value}
        for m in matches:
            mid = m.get("match_id")
            state = m.get("state")
            if mid is None:
                continue
            finished = state == models.MatchState.FINISHED.value
            if finished and stored.get(mid) == models.MatchState.FINISHED.value:
                continue
            if not (finished or state in live_states):
                continue
            try:
                events = self._client.events(mid)
                detail = self._client.match(mid)
                detail_obj = detail[0] if isinstance(detail, list) and detail else detail
                rows = parse_player_stats(mid, events, detail_obj)
                player_store.upsert(self._player_store, mid, state, rows)
            except Exception:
                logger.exception("player stats update failed for match %s", mid)

    def team_leaders(self, team: str) -> dict:
        """Per-stat ranked leader rows for `team` aggregated across its matches.

        Returns {"goals"|"assists"|"cards"|"rating": [{player, value, apps}, ...]}.
        Players are grouped by playerId when present, else normalized name. Each
        list is filtered to players with a value for that stat and sorted desc.
        """
        if self._player_store is None:
            return {}
        by_match = player_store.load(self._player_store)
        target = canonical_team(team)
        groups: dict = {}
        for rows in by_match.values():
            for r in rows:
                if canonical_team(r.team) != target:
                    continue
                key = r.player_id if r.player_id else r.player.strip().lower()
                g = groups.get(key)
                if g is None:
                    g = {"player": r.player, "goals": 0, "assists": 0,
                         "yellow": 0, "red": 0, "ratings": [], "matches": set()}
                    groups[key] = g
                if len(r.player) > len(g["player"]):
                    g["player"] = r.player        # prefer the fuller name
                g["goals"] += r.goals
                g["assists"] += r.assists
                g["yellow"] += r.yellow
                g["red"] += r.red
                if r.rating is not None:
                    g["ratings"].append(r.rating)
                g["matches"].add(r.match_id)

        def ranked(value_fn, keep_fn):
            out = [{"player": g["player"], "value": value_fn(g), "apps": len(g["matches"])}
                   for g in groups.values() if keep_fn(g)]
            out.sort(key=lambda d: d["value"], reverse=True)
            return out

        return {
            "goals": ranked(lambda g: g["goals"], lambda g: g["goals"] > 0),
            "assists": ranked(lambda g: g["assists"], lambda g: g["assists"] > 0),
            "cards": ranked(lambda g: g["yellow"] + g["red"],
                            lambda g: (g["yellow"] + g["red"]) > 0),
            "rating": ranked(lambda g: round(sum(g["ratings"]) / len(g["ratings"]), 2),
                             lambda g: len(g["ratings"]) > 0),
        }

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
            "kickoff": m.kickoff.isoformat() if m.kickoff else None,
        }


def next_delay(snapshot: dict) -> int:
    """Adaptive poll cadence (seconds): fast while any match is live, slow when idle."""
    return 60 if snapshot.get("any_live") else 1800
