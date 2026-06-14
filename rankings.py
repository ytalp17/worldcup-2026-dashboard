#!/usr/bin/env python3
"""FIFA ranking integration for the 48 World Cup 2026 teams.

Using the official FIFA ranking (11 June 2026 update), this:
  1. downloads each team's national flag into assets/flags/<Team>.png
     (named by the canonical team name in assets/data/teams.csv, matching the
     assets/country_logos convention), and
  2. appends a `fifa_rank` column to assets/data/teams.csv.

Teams are joined to the ranking by FIFA 3-letter code. Run from the repo root:

    python rankings.py

Re-run to refresh flags / ranks (overwrites in place). Requires network access
to flagcdn.com.
"""

import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
TEAMS_CSV = ROOT / "assets" / "data" / "teams.csv"
FLAGS_DIR = ROOT / "assets" / "flags"

# rank, FIFA code, team name, points, movement (+ up / - down vs previous).
# Pulled directly from the official 11 June 2026 ranking for the 48 qualified teams.
ROWS = [
    (1,  "ARG", "Argentina",          1877.27,  0),
    (2,  "ESP", "Spain",              1874.71,  0),
    (3,  "FRA", "France",             1870.70,  0),
    (4,  "ENG", "England",            1828.02,  0),
    (5,  "POR", "Portugal",           1767.85,  0),
    (6,  "BRA", "Brazil",             1765.34,  0),
    (7,  "MAR", "Morocco",            1755.62,  0),
    (8,  "NED", "Netherlands",        1753.57,  0),
    (9,  "BEL", "Belgium",            1742.24,  0),
    (10, "GER", "Germany",            1735.77,  0),
    (11, "CRO", "Croatia",            1714.87,  0),
    (13, "MEX", "Mexico",             1700.98,  1),
    (14, "COL", "Colombia",           1698.35, -1),
    (15, "USA", "USA",                1688.53,  2),
    (16, "SEN", "Senegal",            1684.07, -1),
    (17, "URU", "Uruguay",            1673.07, -1),
    (18, "JPN", "Japan",              1661.58,  0),
    (19, "SUI", "Switzerland",        1640.93,  0),
    (20, "IRN", "IR Iran",            1619.58,  0),
    (22, "KOR", "Korea Republic",     1612.55,  3),
    (23, "AUS", "Australia",          1605.61,  4),
    (24, "ECU", "Ecuador",            1598.52, -1),
    (25, "AUT", "Austria",            1597.40, -1),
    (27, "TUR", "Türkiye",            1579.47, -5),
    (28, "ALG", "Algeria",            1571.03,  0),
    (29, "EGY", "Egypt",              1562.37,  0),
    (30, "NOR", "Norway",             1557.44,  1),
    (31, "CAN", "Canada",             1551.50, -1),
    (33, "CIV", "Côte d'Ivoire",      1540.87,  0),
    (34, "PAN", "Panama",             1539.16,  0),
    (37, "SCO", "Scotland",           1518.77,  5),
    (39, "SWE", "Sweden",             1509.79, -1),
    (42, "PAR", "Paraguay",           1488.05, -1),
    (43, "CZE", "Czechia",            1484.82, -3),
    (45, "TUN", "Tunisia",            1476.41,  0),
    (46, "COD", "Congo DR",           1474.43,  0),
    (50, "QAT", "Qatar",              1459.45,  6),
    (51, "UZB", "Uzbekistan",         1458.73, -1),
    (57, "IRQ", "Iraq",               1446.28,  0),
    (60, "KSA", "Saudi Arabia",       1423.88,  1),
    (61, "RSA", "South Africa",       1414.88, -1),
    (63, "BIH", "Bosnia and Herzegovina", 1395.19, 1),
    (64, "JOR", "Jordan",             1387.74, -1),
    (67, "CPV", "Cabo Verde",         1371.11,  0),
    (82, "CUW", "Curaçao",            1294.77,  0),
    (84, "HAI", "Haiti",              1277.67, -1),
    (85, "NZL", "New Zealand",        1275.58,  0),
    (73, "GHA", "Ghana",              1346.88,  0),
]

# FIFA 3-letter -> ISO 3166-1 alpha-2 (for flagcdn.com). England/Scotland use
# the GB subdivision codes so you get the correct national flags.
FIFA_TO_ISO2 = {
    "CAN":"ca","MEX":"mx","USA":"us","ARG":"ar","BRA":"br","COL":"co","ECU":"ec","PAR":"py",
    "URU":"uy","ENG":"gb-eng","FRA":"fr","CRO":"hr","NOR":"no","POR":"pt","GER":"de","NED":"nl",
    "AUT":"at","BEL":"be","SCO":"gb-sct","ESP":"es","SUI":"ch","SWE":"se","TUR":"tr","BIH":"ba",
    "CZE":"cz","ALG":"dz","CPV":"cv","CIV":"ci","EGY":"eg","GHA":"gh","MAR":"ma","SEN":"sn",
    "RSA":"za","TUN":"tn","COD":"cd","AUS":"au","IRN":"ir","JPN":"jp","JOR":"jo","KOR":"kr",
    "QAT":"qa","KSA":"sa","UZB":"uz","IRQ":"iq","CUW":"cw","HAI":"ht","PAN":"pa","NZL":"nz",
}

RANK_BY_CODE = {code: rank for rank, code, _team, _pts, _move in ROWS}


def _download_flag(iso: str, dest: Path, session: requests.Session) -> None:
    url = f"https://flagcdn.com/w160/{iso}.png"
    resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def main() -> None:
    teams = pd.read_csv(TEAMS_CSV)

    # Fail loud if the ranking source doesn't cover every team in teams.csv.
    missing_rank = sorted(c for c in teams["code"] if c not in RANK_BY_CODE)
    missing_iso = sorted(c for c in teams["code"] if c not in FIFA_TO_ISO2)
    if missing_rank:
        raise SystemExit(f"No FIFA rank for codes: {missing_rank}")
    if missing_iso:
        raise SystemExit(f"No ISO flag code for: {missing_iso}")

    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    failed = []
    for _, row in teams.iterrows():
        code, team = row["code"], row["team"]
        dest = FLAGS_DIR / f"{team}.png"
        try:
            _download_flag(FIFA_TO_ISO2[code], dest, session)
            print(f"  #{RANK_BY_CODE[code]:<3} {team:<24} flag -> {dest.name}")
            time.sleep(0.2)
        except requests.RequestException as exc:
            print(f"  ! flag failed for {team} ({code}): {exc}")
            failed.append(team)

    teams["fifa_rank"] = teams["code"].map(RANK_BY_CODE)
    teams.to_csv(TEAMS_CSV, index=False)

    print(f"\nAppended fifa_rank to {TEAMS_CSV.name}; "
          f"saved {len(teams) - len(failed)}/{len(teams)} flags to {FLAGS_DIR}/")
    if failed:
        raise SystemExit(f"Flag download failed for: {failed}")


if __name__ == "__main__":
    main()
