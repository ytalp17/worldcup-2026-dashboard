#!/usr/bin/env python3
"""Download a national flag for each WC2026 head coach's nationality into
assets/manager_flags/<Country>.png.

Nationalities come from the cleaned coach_nationality in assets/data/teams.csv
(see src.data.team_continents.manager_nationality_for), so the filenames match
exactly what the app looks up at render time. Run from the repo root:

    python scripts/download_manager_flags.py

Requires network access to flagcdn.com. Re-run to refresh (overwrites in place).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.team_continents import (  # noqa: E402
    TEAM_MANAGER_NATIONALITY,
    manager_nationality_for,
)

FLAGS_DIR = ROOT / "assets" / "manager_flags"

# Canonical manager nationality -> ISO 3166-1 alpha-2 (for flagcdn.com).
# England/Scotland use GB subdivision codes; the free-text "UK" maps to gb.
NATIONALITY_TO_ISO2 = {
    "Argentina": "ar", "Australia": "au", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Cape Verde": "cv", "Croatia": "hr",
    "Czechia": "cz", "Egypt": "eg", "England": "gb-eng", "France": "fr",
    "Germany": "de", "Greece": "gr", "Iran": "ir", "Italy": "it",
    "Ivory Coast": "ci", "Japan": "jp", "Korea Republic": "kr", "Mexico": "mx",
    "Morocco": "ma", "Netherlands": "nl", "Norway": "no", "Portugal": "pt",
    "Scotland": "gb-sct", "Senegal": "sn", "Spain": "es", "Switzerland": "ch",
    "UK": "gb", "USA": "us",
}


def main() -> None:
    nationalities = sorted(
        {manager_nationality_for(t) for t in TEAM_MANAGER_NATIONALITY} - {None}
    )
    missing = [n for n in nationalities if n not in NATIONALITY_TO_ISO2]
    if missing:
        raise SystemExit(f"No ISO flag code for nationalities: {missing}")

    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    failed = []
    for nat in nationalities:
        url = f"https://flagcdn.com/w160/{NATIONALITY_TO_ISO2[nat]}.png"
        try:
            resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            resp.raise_for_status()
            (FLAGS_DIR / f"{nat}.png").write_bytes(resp.content)
            print(f"  {nat:28} -> {nat}.png")
            time.sleep(0.2)
        except requests.RequestException as exc:
            print(f"  ! flag failed for {nat}: {exc}")
            failed.append(nat)

    print(f"\nSaved {len(nationalities) - len(failed)}/{len(nationalities)} "
          f"manager flags to {FLAGS_DIR}/")
    if failed:
        raise SystemExit(f"Flag download failed for: {failed}")


if __name__ == "__main__":
    main()
