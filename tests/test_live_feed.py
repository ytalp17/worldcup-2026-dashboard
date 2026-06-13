from __future__ import annotations

from src.data.live.service import next_delay


def test_next_delay_fast_when_live():
    assert next_delay({"any_live": True}) == 60


def test_next_delay_slow_when_idle():
    assert next_delay({"any_live": False}) == 1800


def test_next_delay_defaults_idle_when_missing():
    assert next_delay({}) == 1800
