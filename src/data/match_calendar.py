from __future__ import annotations

from datetime import date

from src.data.matches import Match


class MatchCalendar:
    """Tournament calendar derived from the match schedule.

    Knows the selectable date range (today → final day), which days have
    matches (for blink styling), and which host cities are active on a given
    day (for highlighting the map). ``Match.stadium`` is the generic FIFA name,
    so a ``stadium → city`` map is required to resolve host cities.
    """

    def __init__(
        self,
        matches: list[Match],
        stadium_to_city: dict[str, str],
        today: date,
    ) -> None:
        self._today = today
        self._cities_by_date: dict[date, set[str]] = {}
        for m in matches:
            self._cities_by_date.setdefault(m.date, set())
            city = stadium_to_city.get(m.stadium)
            if city:
                self._cities_by_date[m.date].add(city)
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

    def active_cities(self, day: date) -> set[str]:
        return set(self._cities_by_date.get(day, set()))
