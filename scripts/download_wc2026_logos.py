"""
FIFA World Cup 2026 - Team Logo Downloader
Downloads all 48 team SVG logos from footylogos.com into assets/country_logos/.
Run from the repo root: python scripts/download_wc2026_logos.py
Requires: requests, beautifulsoup4
"""

import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = str(Path(__file__).resolve().parents[1] / "assets" / "country_logos")
BASE_URL = "https://www.footylogos.com/logos/{}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TEAMS = [
    "algeria-national-team",
    "argentina-national-team",
    "australia-national-team",
    "austria-national-team",
    "belgium-national-team",
    "bosnia-and-herzegovina-national-team",
    "brazil-national-team",
    "cabo-verde-national-team",
    "canada-national-team",
    "colombia-national-team",
    "cote-d-ivoire-national-team",
    "croatia-national-team",
    "curacao-national-team",
    "czechia-national-team",
    "dr-congo-national-team",
    "ecuador-national-team",
    "egypt-national-team",
    "england-national-team",
    "france-national-team",
    "germany-national-team",
    "ghana-national-team",
    "haiti-national-team",
    "iran-national-team",
    "iraq-national-team",
    "japan-national-team",
    "jordan-national-team",
    "mexico-national-team",
    "morocco-national-team",
    "netherlands-national-team-dutch",
    "new-zealand-national-team",
    "norway-national-team",
    "panama-national-team",
    "paraguay-national-team",
    "portugal-national-team",
    "qatar-national-team",
    "saudi-arabia-national-team",
    "scotland-national-team",
    "senegal-national-team",
    "south-africa-national-team",
    "south-korea-national-team",
    "spain-national-team",
    "sweden-national-team",
    "switzerland-national-team",
    "tunisia-national-team",
    "turkey-national-team",
    "uruguay-national-team",
    "usa-national-team",
    "uzbekistan-national-team",
]


def get_svg_url(team_slug):
    url = BASE_URL.format(team_slug)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Look for an <a> tag whose text contains "SVG" and href points to a CDN svg
    for a in soup.find_all("a", href=True):
        if a["href"].endswith(".svg") and "website-files.com" in a["href"]:
            return a["href"]

    # Fallback: scan raw HTML for any CDN .svg URL
    match = re.search(
        r"https://cdn\.prod\.website-files\.com/[^\s\"']+\.svg", resp.text
    )
    if match:
        return match.group(0)

    return None


def download_svg(url, filepath):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Saving logos to: {os.path.abspath(OUTPUT_DIR)}/\n")

    success, failed = [], []

    for i, team in enumerate(TEAMS, 1):
        print(f"[{i:02d}/{len(TEAMS)}] {team} ... ", end="", flush=True)
        try:
            svg_url = get_svg_url(team)
            if not svg_url:
                print("X  (no SVG found on page)")
                failed.append(team)
                continue

            filepath = os.path.join(OUTPUT_DIR, f"{team}.svg")
            download_svg(svg_url, filepath)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"OK  ({size_kb:.1f} KB)")
            success.append(team)

        except Exception as e:
            print(f"X  ({e})")
            failed.append(team)

        time.sleep(0.4)  # be polite to the server

    print(f"\n{'='*50}")
    print(f"OK  Downloaded: {len(success)}/{len(TEAMS)}")
    if failed:
        print(f"X  Failed ({len(failed)}):")
        for t in failed:
            print(f"   - {t}")
    print(f"\nLogos saved to: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
