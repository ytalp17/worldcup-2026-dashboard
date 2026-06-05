from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.data.matches import Match


class MatchCalendar:
    """Tournament calendar derived from the match schedule. Knows the date
    range, which days have matches, and which host cities are active on a given
    day — by venue date, or by the viewer's local date when a timezone is given."""

    def __init__(
        self,
        matches: list[Match],
        stadium_to_city: dict[str, str],
        today: date,
    ) -> None:
        self._today = today
        self._cities_by_date: dict[date, set[str]] = {}
        # (kickoff_utc, city) for the user-local computation.
        self._kickoffs: list[tuple] = []
        for m in matches:
            city = stadium_to_city.get(m.stadium)
            if not city:
                continue
            self._cities_by_date.setdefault(m.date, set()).add(city)
            self._kickoffs.append((m.kickoff_utc, city))
        self._end = max(self._cities_by_date) if self._cities_by_date else today

    @property
    def start(self) -> date:
        return self._today

    @property
    def end(self) -> date:
        return self._end

    @property
    def match_dates(self) -> set[date]:
        return set(self._cities_by_date)

    def active_cities(self, day: date, user_tz: str | None = None) -> set[str]:
        """Host cities with a match on `day`. With `user_tz`, `day` is compared
        against each kickoff converted to that zone; otherwise against the venue
        date. Unknown/invalid `user_tz` falls back to venue dates."""
        if user_tz:
            try:
                zone = ZoneInfo(user_tz)
            except (ZoneInfoNotFoundError, ValueError):
                zone = None
            if zone is not None:
                return {
                    city for kickoff_utc, city in self._kickoffs
                    if kickoff_utc.astimezone(zone).date() == day
                }
        return set(self._cities_by_date.get(day, set()))
