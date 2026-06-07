#!/usr/bin/env python3
"""
Scrape MyLineups (mylineups.app) for all 48 World Cup 2026 starting XIs.

Output: lineups.json — a dict keyed by team slug, each entry:
    {
      "name": "Argentina",
      "formation": "433",          # digits only, ready for mplsoccer
      "coach": "Lionel Scaloni",   # "" if not listed
      "xi": [["Martínez", 23], ["Molina", 26], ...]   # 11 starters, GK first
    }

This feeds directly into wc2026_pitches.py (drop the JSON in as LINEUPS).

Why this works without proxies: MyLineups is static Astro-generated HTML and
did not block automated requests in testing (unlike Transfermarkt). Still, we
keep a polite delay and a real User-Agent.

Usage:
    pip install requests beautifulsoup4
    python scrape_mylineups.py
"""

import json
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://mylineups.app/world-cup-2026/teams/"
DELAY = 1.5  # seconds between requests — be polite
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
}

# All 48 team slugs exactly as they appear in MyLineups URLs.
SLUGS = [
    "algeria", "argentina", "australia", "austria", "belgium",
    "bosnia-and-herzegovina", "brazil", "canada", "cape-verde", "colombia",
    "croatia", "curacao", "czechia", "dr-congo", "ecuador", "egypt",
    "england", "france", "germany", "ghana", "haiti", "iran", "iraq",
    "ivory-coast", "japan", "jordan", "mexico", "morocco", "netherlands",
    "new-zealand", "norway", "panama", "paraguay", "portugal", "qatar",
    "saudi-arabia", "scotland", "senegal", "south-africa", "south-korea",
    "spain", "sweden", "switzerland", "tunisia", "turkiye", "uruguay",
    "usa", "uzbekistan",
]


def clean_formation(text):
    """'4-3-3' -> '433'. Returns '' if no formation pattern found."""
    m = re.search(r"\b(\d(?:-\d){1,3})\b", text)
    return m.group(1).replace("-", "") if m else ""


def parse_team(html, slug):
    """Extract name, formation, coach, and the 11 starters from a team page."""
    soup = BeautifulSoup(html, "html.parser")

    # --- name (h1) ---
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else slug.replace("-", " ").title()
    # h1 sometimes includes the formation; strip trailing digits/dashes
    name = re.sub(r"\s*\d(?:-\d){1,3}\s*$", "", name).strip()

    # --- formation ---
    # Prefer the page's own description meta, fall back to scanning text.
    formation = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        formation = clean_formation(meta["content"])
    if not formation:
        formation = clean_formation(soup.get_text(" ", strip=True))

    # --- coach (optional) ---
    coach = ""
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"Head coach\s+([A-ZÀ-Þ][\w'.\- ]+?)\s+(?:Avg|Starter|$)", txt)
    if m:
        coach = m.group(1).strip()
    else:
        m = re.search(r"led by ([A-ZÀ-Þ][\w'.\- ]+?)[.,]", txt)
        if m:
            coach = m.group(1).strip()

    # --- starting XI ---
    # The squad list renders each player as a row carrying a position label
    # (GK/DEF/MID/ATT), a shirt number, and a surname. We collect rows in
    # document order; the first 11 are the starters (page shows "11 starters"
    # before "15 bench"). We detect rows via the position-badge text.
    players = []
    # Primary: scan <li> rows (Astro typically renders the squad list as a
    # list). Fallback: if that yields too few, scan the full page text line by
    # line for the same "POS NUM Surname" pattern, which is layout-independent.
    def collect_from(elements):
        found = []
        for el in elements:
            t = el.get_text(" ", strip=True)
            m = re.match(r"^(GK|DEF|MID|ATT)\s+(\d{1,2})\s+(.+?)$", t)
            if m:
                pos, num, surname = m.group(1), int(m.group(2)), m.group(3).strip()
                surname = re.split(r"\s{2,}", surname)[0].strip()
                found.append((pos, num, surname))
        return found

    players = collect_from(soup.find_all("li"))
    if len(players) < 11:
        # fallback: try common row containers
        players = collect_from(soup.find_all(["div", "a", "tr", "p"]))
    if len(players) < 11:
        # last resort: line-by-line over the whole rendered text
        for line in soup.get_text("\n", strip=True).splitlines():
            m = re.match(r"^(GK|DEF|MID|ATT)\s+(\d{1,2})\s+(.+?)$", line.strip())
            if m:
                players.append((m.group(1), int(m.group(2)), m.group(3).strip()))

    # de-dupe while preserving order (the pitch section can repeat names)
    seen = set()
    ordered = []
    for pos, num, surname in players:
        key = (num, surname)
        if key not in seen:
            seen.add(key)
            ordered.append((pos, num, surname))

    # first 11 are starters
    starters = ordered[:11]

    # mplsoccer wants GK first, then defence, midfield, attack — which is the
    # squad-list order already. Sort defensively by position rank just in case.
    rank = {"GK": 0, "DEF": 1, "MID": 2, "ATT": 3}
    starters.sort(key=lambda p: rank.get(p[0], 9))

    xi = [[surname, num] for pos, num, surname in starters]

    return {"name": name, "formation": formation, "coach": coach, "xi": xi}


def main():
    out = {}
    problems = []
    for i, slug in enumerate(SLUGS, 1):
        url = BASE + slug
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            team = parse_team(r.text, slug)
        except Exception as e:
            print(f"[{i}/48] {slug}: ERROR {e}", file=sys.stderr)
            problems.append(slug)
            time.sleep(DELAY)
            continue

        n = len(team["xi"])
        flag = "" if (n == 11 and team["formation"]) else "  <-- CHECK"
        print(f"[{i}/48] {team['name']:<22} {team['formation'] or '???':<6} "
              f"{n} players{flag}")
        if n != 11 or not team["formation"]:
            problems.append(slug)
        out[slug] = team
        time.sleep(DELAY)

    out_path = "assets/data/estimated_starting_eleven.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {out_path} with {len(out)} teams.")
    if problems:
        print(f"Teams needing a manual look ({len(problems)}): "
              f"{', '.join(problems)}")
        print("Open those pages in a browser and fix the entry in lineups.json.")
    else:
        print("All 48 parsed cleanly with 11 players and a formation.")


if __name__ == "__main__":
    main()
