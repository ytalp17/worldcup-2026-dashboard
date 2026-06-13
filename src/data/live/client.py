from __future__ import annotations

import requests

BASE_URL = "https://soccer.highlightly.net"
_TIMEOUT = 10


class HighlightlyError(Exception):
    """Base error for the Highlightly client."""


class RateLimitError(HighlightlyError):
    """Raised on HTTP 429 (quota exhausted)."""


class HighlightlyClient:
    """Thin synchronous wrapper over the Highlightly football API.

    This is the ONLY component that performs network IO. Returns raw dicts;
    parsing into domain models happens in models.py.
    """

    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.requests_remaining: int | None = None

    def _get(self, path: str, params: dict) -> dict | list:
        resp = requests.get(
            f"{self._base_url}{path}",
            headers={"x-rapidapi-key": self._api_key},
            params=params,
            timeout=_TIMEOUT,
        )
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining is not None:
            self.requests_remaining = int(remaining)
        if resp.status_code == 429:
            raise RateLimitError("Highlightly quota exhausted")
        if resp.status_code != 200:
            raise HighlightlyError(f"HTTP {resp.status_code} for {path}")
        return resp.json()

    def matches(self, date: str, league_id: int) -> dict:
        return self._get("/matches", {"date": date, "leagueId": league_id})

    def match(self, match_id: int) -> list:
        # /matches/{id} returns a bare list of one detailed match object.
        return self._get(f"/matches/{match_id}", {})

    def events(self, match_id: int) -> list:
        # /events/{id} returns a bare list of event objects.
        return self._get(f"/events/{match_id}", {})

    def statistics(self, match_id: int) -> list:
        # /statistics/{id} returns a bare list of two team-statistics objects.
        return self._get(f"/statistics/{match_id}", {})

    def lineups(self, match_id: int) -> dict:
        return self._get(f"/lineups/{match_id}", {})

    def standings(self, league_id: int, season: int) -> dict:
        return self._get("/standings", {"leagueId": league_id, "season": season})
