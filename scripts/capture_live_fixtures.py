"""Capture real Highlightly responses into tests/fixtures/live/ so model
parsing can be developed and tested offline. Run once:
    set -a; source .env; set +a
    python scripts/capture_live_fixtures.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.data.live.client import HighlightlyClient

LEAGUE_ID = 1635
SEASON = 2026
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "live"


def main() -> None:
    key = os.environ["HIGHLIGHTLY_API_KEY"]
    client = HighlightlyClient(api_key=key)
    OUT.mkdir(parents=True, exist_ok=True)

    today = client.matches(date="2026-06-13", league_id=LEAGUE_ID)
    (OUT / "matches.json").write_text(json.dumps(today, indent=2))
    print(f"matches: {len(today.get('data', today))} rows; "
          f"remaining={client.requests_remaining}")

    standings = client.standings(league_id=LEAGUE_ID, season=SEASON)
    (OUT / "standings.json").write_text(json.dumps(standings, indent=2))

    rows = today.get("data", today)
    if rows:
        mid = rows[0]["id"]
        (OUT / "match.json").write_text(json.dumps(client.match(mid), indent=2))
        (OUT / "events.json").write_text(json.dumps(client.events(mid), indent=2))
        (OUT / "lineups.json").write_text(json.dumps(client.lineups(mid), indent=2))


if __name__ == "__main__":
    main()
