"""Headless end-to-end check for the Team-mode group-standings panel.

Boots the app, verifies: Time mode shows no open panel; toggling Team mode opens
the left panel (4 rows + flags + a "Group X" title) and shrinks the map to ~2/3
with tiles still loaded; navigating the carousel updates the table; the theme
switch flips the ag-grid theme; and the mobile viewport stacks without h-overflow.

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
PORT = 8054
URL = f"http://127.0.0.1:{PORT}/"


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
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="load")
        page.wait_for_selector(".leaflet-marker-icon", timeout=15000)
        time.sleep(1)

        # --- Time mode (default): panel collapsed, not open ---
        print("Time mode:")
        panel_class = page.get_attribute("#group-panel", "class") or ""
        check("panel present", page.query_selector("#group-panel") is not None)
        check("panel NOT open by default", "group-panel--open" not in panel_class)
        map_box0 = page.query_selector("#map-container").bounding_box()
        check("map ~full width in time mode", map_box0["width"] > 1100)

        # --- Toggle Team mode ---
        print("Toggle Team mode:")
        page.locator("#mode-toggle").click(force=True)
        page.wait_for_selector("#group-panel.group-panel--open", timeout=8000)
        page.wait_for_selector(".group-grid .ag-row", timeout=8000)
        time.sleep(1.5)  # allow the flex-basis transition + resize to settle

        rows = page.query_selector_all(".group-grid .ag-row")
        flags = page.query_selector_all(".team-cell__flag")
        title = (page.inner_text("#group-table-title") or "").strip()
        check("panel opened", page.query_selector("#group-panel.group-panel--open") is not None)
        check("exactly 4 standings rows", len(rows) == 4)
        check("4 team flags rendered", len(flags) == 4)
        check("group title looks like 'Group X'", title.startswith("Group ") and len(title) <= 8)

        # No numeric DATA cell clips its stat to an ellipsis (the regression we
        # fixed: quartz's wide padding made "0" render as "0…"). Header cells have
        # ~3px internal wrapper overflow that doesn't clip text, and the Team cell
        # intentionally ellipsises long names, so both are excluded here.
        clipped = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.group-grid .ag-cell.group-grid__num'))"
            ".filter(c => c.scrollWidth > c.clientWidth + 1).length"
        )
        check("no clipped numeric stat cells", clipped == 0)

        # map shrank to roughly 2/3, panel took ~1/3, tiles still loaded
        map_box1 = page.query_selector("#map-container").bounding_box()
        panel_box1 = page.query_selector("#group-panel").bounding_box()
        tiles = page.query_selector_all(".leaflet-tile-loaded")
        check("map shrank from full width", map_box1["width"] < map_box0["width"] - 200)
        check("panel width is ~1/3 (300-520px)", 300 <= panel_box1["width"] <= 520)
        check("map tiles still loaded after resize", len(tiles) > 0)
        check("panel is left of map", panel_box1["x"] < map_box1["x"])

        # --- Navigate carousel: table should follow ---
        print("Carousel navigation:")
        changed_title = title
        for _ in range(12):
            page.locator("#carousel-next").click(force=True)
            time.sleep(0.3)
            t = (page.inner_text("#group-table-title") or "").strip()
            if t != title:
                changed_title = t
                break
        rows2 = page.query_selector_all(".group-grid .ag-row")
        check("group title changed after navigating", changed_title != title)
        check("still 4 rows after navigation", len(rows2) == 4)

        # --- Theme toggle flips the grid theme ---
        print("Theme toggle:")
        grid_class_before = page.get_attribute("#group-grid", "class") or ""
        page.locator("#color-scheme-toggle").click(force=True)
        time.sleep(0.6)
        grid_class_after = page.get_attribute("#group-grid", "class") or ""
        check("grid had dark quartz theme", "ag-theme-quartz-dark" in grid_class_before)
        check(
            "grid switched to light quartz theme",
            "ag-theme-quartz" in grid_class_after
            and "ag-theme-quartz-dark" not in grid_class_after,
        )
        page.locator("#color-scheme-toggle").click(force=True)  # back to dark
        time.sleep(0.4)

        # --- Mobile: stack, no horizontal overflow ---
        print("Mobile viewport (390px):")
        page.set_viewport_size({"width": 390, "height": 780})
        time.sleep(1)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        m_map = page.query_selector("#map-container").bounding_box()
        m_panel = page.query_selector("#group-panel").bounding_box()
        check("no horizontal overflow on mobile", overflow)
        if m_panel:
            check("panel stacked below map on mobile", m_panel["y"] >= m_map["y"] + m_map["height"] - 5)
        else:
            check("panel stacked below map on mobile", False)

        browser.close()

    failed = [n for n, ok in checks if not ok]
    print()
    print(f"E2E RESULT: {'PASS' if not failed else 'FAIL'}  ({len(checks) - len(failed)}/{len(checks)} checks)")
    if failed:
        print("Failed checks:", failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
