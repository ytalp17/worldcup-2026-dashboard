"""FIFA World Cup 2026 - Stadium Image Downloader.

Reads assets/data/venues.csv (the single source of truth) and
downloads each stadium image into assets/stadiums/ so the Dash app can serve
them from /assets/stadiums/<image_filename>.

Run from anywhere:  python scripts/download_stadium_images.py
"""

from __future__ import annotations

import csv
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import certifi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "assets" / "data" / "venues.csv"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "stadiums"

# FIFA's CDN serves a resized/optimised render only when this transform query
# is appended. The CSV stores the bare URL; we add the transform here.
TRANSFORM_QUERY = "io=transform:fill,width:1366&quality=75"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def _full_url(base_url: str) -> str:
    if not base_url:
        return ""
    return base_url if "io=transform" in base_url else f"{base_url}?{TRANSFORM_QUERY}"


def download_images() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # The python.org framework build on macOS does not use the system trust
    # store, so verify against certifi's CA bundle explicitly.
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    success, failed = 0, []
    for row in rows:
        filename = row["image_filename"].strip()
        url = _full_url(row["image_url"].strip())
        filepath = OUTPUT_DIR / filename

        if not url:
            print(f"✗ {filename}: no URL in CSV")
            failed.append(filename)
            continue

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20, context=ssl_context) as response:
                data = response.read()
            filepath.write_bytes(data)
            print(f"✓ {filename} ({len(data) / 1024:.1f} KB)")
            success += 1
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(f"✗ {filename}: {exc}")
            failed.append(filename)

    print(f"\nDone: {success}/{len(rows)} images saved to '{OUTPUT_DIR}'")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    download_images()
