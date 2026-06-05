"""Offline generator: add a `kickoff_utc` column to the WC2026 match schedule.

Resolves each match's venue-local kickoff (match_date + local_time in the
stadium's IANA zone, DST-correct) to an absolute UTC instant, then OVERWRITES
assets/data/wc2026_matches.csv in place. Re-run whenever the schedule changes:

    ~/anaconda3/bin/conda run -n base python scripts/compute_kickoff_utc.py
"""
from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "assets" / "data"
CSV = DATA / "wc2026_matches.csv"


def to_utc(match_date: str, local_time: str, iana_tz: str) -> str:
    """Combine a venue-local date + 'HH:MM' in `iana_tz`, return the UTC instant
    as an ISO-8601 string with a +00:00 offset."""
    d = datetime.strptime(match_date.strip(), "%Y-%m-%d").date()
    t = time.fromisoformat(local_time.strip())
    local_dt = datetime.combine(d, t, tzinfo=ZoneInfo(iana_tz))
    return local_dt.astimezone(ZoneInfo("UTC")).isoformat()


def stadium_tz_map() -> dict[str, str]:
    """Map generic FIFA stadium name -> IANA timezone, via the venue join."""
    from src.data.host_cities import HostCityRepository
    from src.data.stadiums import StadiumRepository
    from src.data.venues import build_venues

    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, DATA.parent / "stadiums")
    return {v.stadium_name: v.timezone for v in venues}


def main() -> None:
    df = pd.read_csv(CSV)
    tz_by_stadium = stadium_tz_map()
    df["kickoff_utc"] = [
        to_utc(row.match_date, row.local_time, tz_by_stadium[row.stadium])
        for row in df.itertuples(index=False)
    ]
    tmp = CSV.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(CSV)
    print(f"Wrote kickoff_utc for {len(df)} matches -> {CSV}")


if __name__ == "__main__":
    main()
