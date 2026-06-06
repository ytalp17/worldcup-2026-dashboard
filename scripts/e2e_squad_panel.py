"""Headless end-to-end check for the Team-mode squad panel.

Boots the app and verifies: in Time mode the squad card is collapsed/hidden;
toggling Team mode reveals the bento grid and the squad card; the squad ag-grid
renders >=20 player rows; the squad title matches the centered team (default
"Algeria"); the 12 columns overflow the card horizontally; navigating the
carousel updates the title (and ideally the player rows); the color-scheme
switch flips the ag-grid theme class; the map card stays the largest tile; and
the mobile viewport has no horizontal page overflow.

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
PORT = 8056
URL = f"http://127.0.0.1:{PORT}/"
SHOT = f"/tmp/e2e_squad_{PORT}.png"


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

        # --- 1. Time mode (default): squad card collapsed/hidden ---
        print("Time mode (initial):")
        split_class = page.get_attribute("#main-split", "class") or ""
        squad_card = page.query_selector(".bento-card--squad")
        squad_hidden = (
            "main-split--team" not in split_class
            and (squad_card is None or not squad_card.is_visible())
        )
        check("squad card hidden in time mode", squad_hidden)

        # --- 2. Toggle Team mode → bento + squad card visible ---
        print("Toggle Team mode:")
        page.locator("#mode-toggle").click(force=True)
        page.wait_for_selector("#main-split.main-split--team", timeout=8000)
        page.wait_for_selector(".bento-card--squad", timeout=8000)
        page.wait_for_selector("#squad-grid .ag-row", timeout=10000)
        time.sleep(1.5)  # allow layout swap + grid render to settle

        in_team = page.query_selector("#main-split.main-split--team") is not None
        squad_card = page.query_selector(".bento-card--squad")
        squad_visible = squad_card is not None and squad_card.is_visible()
        check("main-split has main-split--team class", in_team)
        check("squad card visible in team mode", squad_visible)

        # --- 3. squad-grid renders >= 20 rows ---
        print("Squad grid rows:")
        rows = page.query_selector_all("#squad-grid .ag-center-cols-viewport .ag-row")
        if len(rows) < 20:
            # fall back to any ag-row inside the grid (virtualization-safe)
            rows = page.query_selector_all("#squad-grid .ag-row")
        check(f"squad grid has >= 20 rows (got {len(rows)})", len(rows) >= 20)

        # --- 4. title non-empty and equals centered team (default Algeria) ---
        print("Squad title:")
        title = (page.inner_text("#squad-table-title") or "").strip()
        check(f"squad title non-empty (got '{title}')", bool(title))
        check(f"squad title is default centered team 'Algeria' (got '{title}')",
              title == "Algeria")

        # --- 5. horizontal scroll present (12 columns overflow) ---
        print("Horizontal overflow:")
        overflow = page.evaluate(
            "() => {"
            " const v = document.querySelector('#squad-grid .ag-center-cols-viewport');"
            " if (!v) return null;"
            " return {sw: v.scrollWidth, cw: v.clientWidth};"
            "}"
        )
        h_ok = overflow is not None and overflow["sw"] > overflow["cw"]
        check(f"squad columns overflow horizontally ({overflow})", h_ok)

        # --- 6. carousel-next advances centered team → title changes ---
        print("Carousel navigation:")
        # Read the pinned-left Player name cell of the top row (row-index 0).
        # The name column is pinned, so it lives outside .ag-center-cols-viewport.
        name_cell_js = (
            "() => { const c = document.querySelector("
            "'#squad-grid .ag-row[row-index=\"0\"] [col-id=\"name\"]');"
            " return c ? c.innerText.trim() : null; }"
        )
        first_row_before = page.evaluate(name_cell_js)
        changed_title = title
        for _ in range(12):
            page.locator("#carousel-next").click(force=True)
            time.sleep(0.4)
            t = (page.inner_text("#squad-table-title") or "").strip()
            if t and t != title:
                changed_title = t
                break
        check(f"title changed after carousel-next ('{title}' -> '{changed_title}')",
              changed_title != title)
        time.sleep(0.6)
        first_row_after = page.evaluate(name_cell_js)
        # bonus: first-row player identity changed too
        check(f"first row player updated (bonus: '{first_row_before}' -> '{first_row_after}')",
              first_row_after != first_row_before)

        # --- 7. color-scheme toggle flips the grid theme class ---
        print("Color-scheme toggle:")
        grid_before = page.get_attribute("#squad-grid", "class") or ""
        page.locator("#color-scheme-toggle").click(force=True)
        time.sleep(0.7)
        grid_after = page.get_attribute("#squad-grid", "class") or ""
        dark_before = "ag-theme-quartz-dark" in grid_before
        dark_after = "ag-theme-quartz-dark" in grid_after
        check(f"squad grid theme flipped (dark {dark_before} -> {dark_after})",
              dark_before != dark_after and "ag-theme-quartz" in grid_after)
        # restore
        page.locator("#color-scheme-toggle").click(force=True)
        time.sleep(0.5)

        # --- 8. map card remains the largest tile ---
        print("Map vs squad size:")
        map_box = page.query_selector(".bento-card--map").bounding_box()
        squad_box = page.query_selector(".bento-card--squad").bounding_box()
        map_area = map_box["width"] * map_box["height"]
        squad_area = squad_box["width"] * squad_box["height"]
        check(f"map card larger than squad card ({map_area:.0f} > {squad_area:.0f})",
              map_area > squad_area)

        # --- screenshot in team mode, desktop viewport ---
        page.screenshot(path=SHOT, full_page=False)
        print(f"  screenshot: {SHOT}")

        # --- 9. mobile viewport: no horizontal page overflow ---
        print("Mobile viewport (390x844):")
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(1)
        # ensure still in team mode (it should persist); re-toggle if not
        if page.query_selector("#main-split.main-split--team") is None:
            page.locator("#mode-toggle").click(force=True)
            page.wait_for_selector("#main-split.main-split--team", timeout=8000)
            time.sleep(1)
        no_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 2"
        )
        check("no horizontal page overflow on mobile", no_overflow)

        browser.close()

    failed = [n for n, ok in checks if not ok]
    print()
    total = len(checks)
    passed = total - len(failed)
    if failed:
        print(f"E2E RESULT: FAIL  ({passed}/{total} checks)")
        print("Failed checks:", failed)
        return 1
    print(f"ALL PASS ({passed}/{total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
