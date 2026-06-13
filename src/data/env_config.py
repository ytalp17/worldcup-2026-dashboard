from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path) -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file into os.environ and return the
    parsed mapping.

    Uses ``setdefault`` so a value already present in the environment (e.g. an
    explicitly exported one) is never overridden. Comments (``#``), blank lines,
    and lines without ``=`` are ignored; surrounding whitespace and matching
    quotes are stripped from values. A missing file is a no-op (returns ``{}``).

    Kept deliberately tiny to avoid a python-dotenv dependency.
    """
    path = Path(path)
    parsed: dict[str, str] = {}
    if not path.exists():
        return parsed
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            parsed[key] = value
            os.environ.setdefault(key, value)
    return parsed
