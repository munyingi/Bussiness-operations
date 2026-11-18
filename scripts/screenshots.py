"""Take a screenshot of every dashboard tab into docs/images/.

    python scripts/screenshots.py            # starts Streamlit itself
    python scripts/screenshots.py --url URL  # use an app that is already running
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
TABS = ["National trend", "Industries", "Municipalities", "Company register", "Top taxpayers", "Data quality", "About"]


def wait_until_idle(page) -> None:
    """Streamlit shows a 'Running...' status widget while a script reruns."""
    page.wait_for_timeout(1500)
    for _ in range(60):
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(2500)  # let charts finish drawing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--chrome", help="path to an existing Chrome/Chromium binary")
    args = parser.parse_args()

    proc = None
    url = args.url
    if not url:
        port = "8599"
        proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
             "--server.headless", "true", "--server.port", port, "--browser.gatherUsageStats", "false"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy(),
        )
        url = f"http://localhost:{port}"
        time.sleep(8)

    OUT.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chrome) if args.chrome else p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=1)
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_selector('[role="tab"]', timeout=120_000)
            wait_until_idle(page)
            for i, name in enumerate(TABS, start=1):
                page.get_by_role("tab", name=name).click()
                wait_until_idle(page)
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                path = OUT / f"{i:02d}-{slug}.png"
                page.screenshot(path=str(path), full_page=True)
                print("saved", path.relative_to(ROOT))
            browser.close()
    finally:
        if proc:
            proc.terminate()


if __name__ == "__main__":
    main()
