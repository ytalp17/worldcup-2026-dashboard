from __future__ import annotations

import os

from src.data.env_config import load_env_file


def test_loads_key_value_pairs(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# a comment\n\nFOO=bar\nHIGHLIGHTLY_API_KEY=abc123\n")
    os.environ.pop("FOO", None)
    os.environ.pop("HIGHLIGHTLY_API_KEY", None)
    parsed = load_env_file(env)
    assert parsed["FOO"] == "bar"
    assert parsed["HIGHLIGHTLY_API_KEY"] == "abc123"
    assert os.environ["FOO"] == "bar"
    assert os.environ["HIGHLIGHTLY_API_KEY"] == "abc123"
    os.environ.pop("FOO", None)
    os.environ.pop("HIGHLIGHTLY_API_KEY", None)


def test_does_not_override_already_set_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("FOO=fromfile\n")
    os.environ["FOO"] = "preset"
    load_env_file(env)
    assert os.environ["FOO"] == "preset"  # setdefault: an exported value wins
    os.environ.pop("FOO", None)


def test_missing_file_is_noop(tmp_path):
    assert load_env_file(tmp_path / "nope.env") == {}


def test_strips_quotes_and_surrounding_whitespace(tmp_path):
    env = tmp_path / ".env"
    env.write_text('FOO = "quoted value" \n')
    os.environ.pop("FOO", None)
    parsed = load_env_file(env)
    assert parsed["FOO"] == "quoted value"
    os.environ.pop("FOO", None)
