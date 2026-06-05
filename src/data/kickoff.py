from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.data.matches import Match


@dataclass(frozen=True)
class KickoffView:
    user_time: str | None     # "HH:MM" in the user's zone (None if tz unknown)
    user_date: date | None    # user-local date (None if tz unknown)
    venue_time: str           # "HH:MM" venue clock
    venue_day_offset: int     # venue_date - user_local_date, in days
    same_clock: bool          # True when tz unknown OR identical clock+day


def kickoff_view(match: Match, user_tz: str | None) -> KickoffView:
    """Resolve a match's kickoff into the viewer's zone. Falls back to
    venue-only (same_clock=True) when the timezone is missing or invalid."""
    venue_time = match.local_time.strftime("%H:%M")
    if not user_tz:
        return KickoffView(None, None, venue_time, 0, True)
    try:
        zone = ZoneInfo(user_tz)
    except (ZoneInfoNotFoundError, ValueError):
        return KickoffView(None, None, venue_time, 0, True)

    local = match.kickoff_utc.astimezone(zone)
    user_time = local.strftime("%H:%M")
    user_date = local.date()
    venue_day_offset = (match.date - user_date).days
    same_clock = user_time == venue_time and venue_day_offset == 0
    return KickoffView(user_time, user_date, venue_time, venue_day_offset, same_clock)


def venue_offset_tag(offset: int) -> str:
    """e.g. -1 -> '(-1d)', +2 -> '(+2d)', 0 -> ''."""
    if offset == 0:
        return ""
    return f"({'+' if offset > 0 else '-'}{abs(offset)}d)"
