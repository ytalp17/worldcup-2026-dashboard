"""Headless end-to-end check: boot the app, click a map marker, assert the
stadium drawer opens with photo + stats. Not part of the test suite (requires
a browser); run manually for interactive verification."""

import sys
import threading
import time
from pathlib import Path

# Ensure this project's app.py wins over any sibling project on sys.path.
_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _ROOT)

CHROMIUM = (
    Path.home()
    / "Library/Caches/ms-playwright/chromium-1155/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
)
PORT = 8053
URL = f"http://127.0.0.1:{PORT}/"


def _serve():
    import app

    app.app.run(port=PORT, debug=False, use_reloader=False)


def main() -> int:
    threading.Thread(target=_serve, daemon=True).start()

    import socket

    for _ in range(60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", PORT)) == 0:
                break
        time.sleep(0.5)
    else:
        print("server never came up")
        return 1
    time.sleep(1)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROMIUM), headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="load")

        page.wait_for_selector(".leaflet-marker-icon", timeout=15000)
        markers = page.query_selector_all(".leaflet-marker-icon")
        print(f"markers rendered: {len(markers)}")

        # Drawer should be closed initially.
        assert page.query_selector(".mantine-Drawer-content") is None, "drawer open too early"

        markers[0].click(force=True)
        page.wait_for_selector(".mantine-Drawer-content", timeout=8000)
        time.sleep(1)

        title = page.inner_text(".mantine-Drawer-title")
        body = page.inner_text(".mantine-Drawer-content").lower()
        img = page.query_selector(".mantine-Drawer-content img")
        img_src = img.get_attribute("src") if img else None

        print(f"drawer title: {title!r}")
        print(f"has capacity badge: {'capacity' in body}")
        print(f"has opened badge: {'opened' in body}")
        print(f"drawer image src: {img_src}")

        ok = bool(title) and "capacity" in body and "opened" in body and bool(img_src)
        browser.close()
        print("E2E RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
