"""Precompute each team's group-stage travel distance into a CSV.

Run from the repo root:  python3 scripts/compute_team_distances.py
Regenerate this whenever the match schedule or venues change.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.flows import build_team_flows, path_distance_km  # noqa: E402
from src.data.host_cities import HostCityRepository  # noqa: E402
from src.data.matches import MatchRepository  # noqa: E402
from src.data.stadiums import StadiumRepository  # noqa: E402
from src.data.venues import build_venues  # noqa: E402

DATA = ROOT / "assets" / "data"
IMAGE_DIR = ROOT / "assets" / "stadiums"
OUT = DATA / "team_distances.csv"


def main() -> None:
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    flows = build_team_flows(matches, venues)

    rows = [
        {"team": team, "distance_km": round(path_distance_km(flow.stops), 1)}
        for team, flow in flows.items()
    ]
    df = pd.DataFrame(rows).sort_values("team").reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")


if __name__ == "__main__":
    main()
