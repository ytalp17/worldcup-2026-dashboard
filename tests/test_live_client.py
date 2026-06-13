from __future__ import annotations

import pytest

from src.data.live.client import HighlightlyClient, RateLimitError


class _FakeResponse:
    def __init__(self, status, payload, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_matches_calls_correct_url_and_headers(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return _FakeResponse(200, {"data": [{"id": 1}]},
                             {"x-ratelimit-requests-remaining": "99"})

    monkeypatch.setattr("src.data.live.client.requests.get", fake_get)
    client = HighlightlyClient(api_key="KEY")
    out = client.matches(date="2026-06-13", league_id=1635)

    assert captured["url"] == "https://soccer.highlightly.net/matches"
    assert captured["headers"]["x-rapidapi-key"] == "KEY"
    assert captured["params"] == {"date": "2026-06-13", "leagueId": 1635}
    assert out == {"data": [{"id": 1}]}
    assert client.requests_remaining == 99


def test_rate_limit_raises(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(429, {}, {})
    monkeypatch.setattr("src.data.live.client.requests.get", fake_get)
    client = HighlightlyClient(api_key="KEY")
    with pytest.raises(RateLimitError):
        client.matches(date="2026-06-13", league_id=1635)
