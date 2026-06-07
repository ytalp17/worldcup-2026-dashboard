"""Headless end-to-end check for the Team-mode estimated-XI formation pitch.

Boots the app and verifies: in Time mode the formation card is hidden; toggling
Team mode reveals it in cell e2; the pitch image renders (a -dark.png src that
actually loads with non-zero natural width); the header shows a hyphenated
formation; advancing the carousel updates both the image src and the title; the
color-scheme switch flips the pitch image between -dark.png and -light.png; and
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
PORT = 8058
URL = f"http://127.0.0.1:{PORT}/"
SHOT = f"/tmp/e2e_formation_{PORT}.png"


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

        # --- 1. Time mode (default): formation card hidden ---
        fc = page.locator(".bento-card--formation")
        check("formation card hidden in Time mode", not fc.is_visible())

        # --- 2. Team mode reveals the formation card in e2 ---
        page.locator("#mode-toggle").click(force=True)
        page.wait_for_selector("#main-split.main-split--team", timeout=8000)
        page.wait_for_selector(".bento-card--formation", timeout=8000)
        check("formation card visible in Team mode", fc.is_visible())

        # The card sits in grid-area e2 (bottom-left, below the map).
        area = page.eval_on_selector(
            ".bento-card--formation",
            "el => getComputedStyle(el).gridArea")
        check(f"formation card occupies grid-area e2 (got '{area}')",
              "e2" in (area or ""))

        # --- 3. pitch image renders and actually loads ---
        page.wait_for_selector("#formation-img", timeout=8000)
        src = page.get_attribute("#formation-img", "src") or ""
        check(f"image src is a dark pitch png ('...{src[-24:]}')",
              src.endswith("-dark.png") and "pitches/" in src)
        nat_w = page.eval_on_selector(
            "#formation-img",
            "el => el.naturalWidth || (el.querySelector('img')||{}).naturalWidth || 0")
        check(f"pitch image actually loaded (naturalWidth={nat_w})", nat_w and nat_w > 0)

        # --- 4. header shows a hyphenated formation for the centred team ---
        title = page.text_content("#formation-title") or ""
        check(f"header shows hyphenated formation ('{title}')",
              "-" in title and "·" in title)

        # --- 5. carousel-next updates image src AND title ---
        for _ in range(3):
            page.locator("#carousel-next").click(force=True)
            time.sleep(0.4)
        new_src = page.get_attribute("#formation-img", "src") or ""
        new_title = page.text_content("#formation-title") or ""
        check(f"pitch src changed after carousel-next ('...{src[-18:]}' -> "
              f"'...{new_src[-18:]}')", new_src != src)
        check(f"title changed after carousel-next ('{title}' -> '{new_title}')",
              new_title != title)

        # --- 6. color-scheme toggle flips dark <-> light pitch image ---
        before = page.get_attribute("#formation-img", "src") or ""
        page.locator("#color-scheme-toggle").click(force=True)
        time.sleep(0.6)
        after = page.get_attribute("#formation-img", "src") or ""
        check(f"theme toggle flips to light png ('...{after[-18:]}')",
              before.endswith("-dark.png") and after.endswith("-light.png"))
        after_w = page.eval_on_selector(
            "#formation-img",
            "el => el.naturalWidth || (el.querySelector('img')||{}).naturalWidth || 0")
        check(f"light pitch image loaded (naturalWidth={after_w})",
              after_w and after_w > 0)
        page.locator("#color-scheme-toggle").click(force=True)  # back to dark
        time.sleep(0.4)

        # --- screenshot in team mode, desktop viewport ---
        page.screenshot(path=SHOT, full_page=False)
        print(f"  screenshot: {SHOT}")

        # --- 7. mobile: no horizontal page overflow ---
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
