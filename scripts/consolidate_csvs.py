"""One-off migration: consolidate the 9 source CSVs (+ 2 .md files) in
assets/data/ into 4 entity CSVs (venues, teams, matches, squads).

Run once from the repo root:  python scripts/consolidate_csvs.py
Committed for reproducibility / audit. Safe to re-run (idempotent).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "assets" / "data"

# Per-venue (city -> IANA timezone, friendly label). Absorbed from the former
# src/data/timezones.py::CITY_TIMEZONES — this is the last place it lives in code
# before moving into venues.csv.
CITY_TIMEZONES = {
    "New York/New Jersey": ("America/New_York", "Eastern Time"),
    "Boston": ("America/New_York", "Eastern Time"),
    "Philadelphia": ("America/New_York", "Eastern Time"),
    "Atlanta": ("America/New_York", "Eastern Time"),
    "Miami": ("America/New_York", "Eastern Time"),
    "Toronto": ("America/Toronto", "Eastern Time"),
    "Dallas": ("America/Chicago", "Central Time"),
    "Houston": ("America/Chicago", "Central Time"),
    "Kansas City": ("America/Chicago", "Central Time"),
    "Mexico City": ("America/Mexico_City", "Central Time"),
    "Monterrey": ("America/Monterrey", "Central Time"),
    "Guadalajara": ("America/Mexico_City", "Central Time"),
    "Seattle": ("America/Los_Angeles", "Pacific Time"),
    "San Francisco": ("America/Los_Angeles", "Pacific Time"),
    "Los Angeles": ("America/Los_Angeles", "Pacific Time"),
    "Vancouver": ("America/Vancouver", "Pacific Time"),
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[/\-]", " ", text.lower())).strip()


def build_venues_csv() -> None:
    cities = pd.read_csv(DATA / "fifa_2026_host_cities.csv")
    stadiums = pd.read_csv(DATA / "fifa_wc2026_stadiums.csv")
    alt = pd.read_csv(DATA / "wc2026_stadium_altitude.csv")
    hc = pd.read_csv(DATA / "host_cities.csv")

    hc["city_join"] = hc["city_name"].replace(
        {"San Francisco Bay Area": "San Francisco"}
    )
    alt_by_city = {r["city"]: r for _, r in alt.iterrows()}
    hc_by_city = {r["city_join"]: r for _, r in hc.iterrows()}
    norm_stadiums = [(_norm(r["Stadium"]), r) for _, r in stadiums.iterrows()]

    rows = []
    for _, c in cities.iterrows():
        city = c["City"]
        key = _norm(city)
        hits = [r for n, r in norm_stadiums if key in n]
        assert len(hits) == 1, f"{city}: expected 1 stadium match, got {len(hits)}"
        s, a, h = hits[0], alt_by_city[city], hc_by_city[city]
        tz, tz_label = CITY_TIMEZONES[city]
        rows.append({
            "city": city,
            "country": c["Country"],
            "official_name": c["Stadium"],
            "stadium_name": s["Stadium"],
            "location": s["Location"],
            "capacity": int(s["Capacity"]),
            "opened": int(s["Opened"]),
            "info": s["Info"],
            "image_filename": s["Image_Filename"],
            "image_url": s["Image_URL"],
            "latitude": c["Latitude"],
            "longitude": c["Longitude"],
            "altitude_m": int(a["altitude_m"]),
            "altitude_ft": int(a["altitude_ft"]),
            "altitude_tier": a["altitude_tier"],
            "region_cluster": h["region_cluster"],
            "airport_code": h["airport_code"],
            "timezone": tz,
            "tz_label": tz_label,
        })
    df = pd.DataFrame(rows)
    assert len(df) == 16, f"expected 16 venues, got {len(df)}"
    df.to_csv(DATA / "venues.csv", index=False)


def _parse_abbreviations() -> dict[str, tuple[str, str]]:
    """Territory -> (code, confederation) from the tab-separated md."""
    out: dict[str, tuple[str, str]] = {}
    for line in (DATA / "fifa_abbrevations.md").read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].strip() != "Code":
            out[parts[0].strip()] = (parts[1].strip(), parts[2].strip())
    return out


def _clean_coach(raw: str) -> str:
    name = raw.lstrip("*").strip()
    if " replaced " in name:
        name = name.split(" replaced ")[0].strip()
    return name.rstrip("*").strip()


def _parse_managers() -> dict[str, tuple[str, str, str]]:
    """canonical team -> (coach, coach_nationality, coach_since)."""
    alias = {
        "Cape Verde": "Cabo Verde", "Curacao": "Curaçao",
        "Czech Republic": "Czechia", "DR Congo": "Congo DR",
        "Iran": "IR Iran", "Ivory Coast": "Côte d'Ivoire", "Turkey": "Türkiye",
    }
    lines = [l.strip() for l in (DATA / "managers.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    recs = lines[5:]  # drop the 5-cell header
    assert len(recs) % 5 == 0, f"managers.md: {len(recs)} record lines not a multiple of 5"
    out: dict[str, tuple[str, str, str]] = {}
    for i in range(0, len(recs), 5):
        team_raw, coach, since, _prev, nat = recs[i:i + 5]
        team = team_raw.lstrip("*").strip()
        team = alias.get(team, team)
        out[team] = (_clean_coach(coach), nat.strip(), since.strip())
    return out


def build_teams_csv() -> None:
    cont = pd.read_csv(DATA / "team_continents.csv")
    dist = pd.read_csv(DATA / "team_distances.csv")
    dist_by = dict(zip(dist["team"], dist["distance_km"]))

    abbr = _parse_abbreviations()
    abbr_alias = {
        "Cabo Verde": "Cape Verde", "Czechia": "Czech Republic",
        "IR Iran": "Iran", "USA": "United States",
    }
    # Teams absent from the abbreviations md — explicit FIFA codes.
    overrides = {
        "Côte d'Ivoire": ("CIV", "CAF"),
        "Scotland": ("SCO", "UEFA"),
        "Türkiye": ("TUR", "UEFA"),
    }
    managers = _parse_managers()

    rows = []
    for _, r in cont.iterrows():
        team = r["team"]
        if team in overrides:
            code, conf = overrides[team]
        else:
            code, conf = abbr[abbr_alias.get(team, team)]
        coach, nat, since = managers.get(team, ("", "", ""))
        rows.append({
            "team": team,
            "continent": r["continent"],
            "distance_km": dist_by[team],
            "code": code,
            "confederation": conf,
            "coach": coach,
            "coach_nationality": nat,
            "coach_since": since,
        })
    df = pd.DataFrame(rows)
    assert len(df) == 48, f"expected 48 teams, got {len(df)}"
    assert (df["code"].str.len() == 3).all(), "every team needs a 3-letter code"
    df.to_csv(DATA / "teams.csv", index=False)


def copy_unchanged() -> None:
    # Byte-for-byte rename (no pandas reserialization that could shift quoting/precision).
    shutil.copyfile(DATA / "wc2026_matches.csv", DATA / "matches.csv")
    shutil.copyfile(DATA / "world_cup_2026_squads.csv", DATA / "squads.csv")


def main() -> None:
    build_venues_csv()
    build_teams_csv()
    copy_unchanged()
    print("Wrote venues.csv, teams.csv, matches.csv, squads.csv")


if __name__ == "__main__":
    main()
