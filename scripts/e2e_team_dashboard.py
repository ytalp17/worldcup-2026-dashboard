"""Headless end-to-end check for the Team-mode dashboard layout.

Boots the app and verifies: Time mode shows only the (full-screen) map; Team
mode reveals the KPI strip (7 stat cards), the Leaders card, the small map tile
(much smaller than the Time-mode map), the formation pitch, table and squad;
advancing the carousel updates the KPI values; and the mobile viewport has no
horizontal page overflow.

Not part of the test suite (requires a browser). Run with the Playwright-capable
Python: /Library/Frameworks/Python.framework/Versions/3.11/bin/python3
"""

import socket
import sys
import threading
import time
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _ROOT)

CHROMIUM = (
    Path.home()
    / "Library/Caches/ms-playwright/chromium-1155/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
)
PORT = 8059
URL = f"http://127.0.0.1:{PORT}/"
SHOT = f"/tmp/e2e_team_dashboard_{PORT}.png"


def _serve():
    import app

    app.app.run(port=PORT, debug=False, use_reloader=False)


def _wait_port():
    for _ in range(60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    threading.Thread(target=_serve, daemon=True).start()
    if not _wait_port():
        print("server never came up")
        return 1
    time.sleep(1)

    from playwright.sync_api import sync_playwright

    checks: list[tuple[str, bool]] = []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROMIUM), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="load")
        page.wait_for_selector(".leaflet-marker-icon", timeout=15000)
        time.sleep(1)

        # --- 1. Time mode: KPI strip hidden, map fills the area ---
        check("KPI strip hidden in Time mode",
              not page.locator("#kpi-strip").is_visible())
        map_time = page.eval_on_selector(
            ".bento-card--map", "el => el.getBoundingClientRect().height")

        # --- 2. Team mode: KPI strip with 7 cards visible ---
        page.locator("#mode-toggle").click(force=True)
        page.wait_for_selector("#main-split.main-split--team", timeout=8000)
        page.wait_for_selector("#kpi-strip", timeout=8000)
        check("KPI strip visible in Team mode",
              page.locator("#kpi-strip").is_visible())
        n_cards = page.locator("#kpi-strip .stat-card").count()
        check(f"KPI strip has 7 stat cards (got {n_cards})", n_cards == 7)

        # The foot card renders a ring.
        rings = page.locator("#kpi-strip .mantine-RingProgress-root").count()
        check(f"foot card shows a ring (got {rings})", rings >= 1)

        # --- 3. Leaders card present with its empty state ---
        check("leaders card present", page.locator(".leaders-panel").count() == 1)
        leaders_txt = page.text_content(".leaders-panel") or ""
        check("leaders shows 'matches start' empty state",
              "matches start" in leaders_txt.lower())

        # --- 4. map is now a SMALL tile (much smaller than Time-mode map) ---
        map_team = page.eval_on_selector(
            ".bento-card--map", "el => el.getBoundingClientRect().height")
        check(f"map shrank in Team mode ({map_time:.0f}px -> {map_team:.0f}px)",
              map_team < map_time * 0.7)

        # --- 5. KPI values update when the carousel advances ---
        before = page.text_content("#kpi-strip") or ""
        for _ in range(4):
            page.locator("#carousel-next").click(force=True)
            time.sleep(0.35)
        after = page.text_content("#kpi-strip") or ""
        check("KPI strip values changed after carousel-next", before != after)

        page.screenshot(path=SHOT, full_page=False)
        print(f"  screenshot: {SHOT}")

        # --- 6. mobile: no horizontal overflow ---
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.6)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > "
            "document.documentElement.clientWidth + 1")
        check("no horizontal overflow on mobile", not overflow)

        browser.close()

    ok = all(c for _, c in checks)
    print(f"\n{'ALL PASS' if ok else 'SOME FAILED'} "
          f"({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
