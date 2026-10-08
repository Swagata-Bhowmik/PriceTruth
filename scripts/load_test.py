"""Concurrent real-browser load test: each user opens the app and completes a price check.

Usage: PRICE_TRUTH_URL=<app url> python scripts/load_test.py --users 25 50 100
Each user is a separate browser context (own session and WebSocket), started together.
"""
import argparse
import asyncio
import json
import os
import time
from datetime import UTC, datetime

import numpy as np
from playwright.async_api import async_playwright

from price_truth.paths import REPORTS


async def user(browser, base: str, start: asyncio.Event) -> dict:
    """Open the dashboard and wait until the default product's verdict and headline figures are shown."""
    context = await browser.new_context()
    page = await context.new_page()
    await start.wait()
    began = time.perf_counter()
    try:
        await page.goto(f"{base}/", timeout=120_000)
        await page.get_by_role("heading", name="Is this a fair price?").wait_for(timeout=120_000)
        loaded = time.perf_counter() - began
        await page.get_by_text("Fair price estimate").first.wait_for(timeout=120_000)
        return {"ok": True, "page_ready_s": loaded, "verdict_s": time.perf_counter() - began}
    except Exception as exc:  # noqa: BLE001 - every failure is recorded as a failed user
        return {"ok": False, "error": type(exc).__name__, "seconds": time.perf_counter() - began}
    finally:
        await context.close()


async def wave(browser, base: str, users: int) -> dict:
    """Release all users at once and summarise their timings."""
    start = asyncio.Event()
    tasks = [asyncio.create_task(user(browser, base, start)) for _ in range(users)]
    await asyncio.sleep(1)
    began = time.perf_counter()
    start.set()
    results = await asyncio.gather(*tasks)
    ok = [r for r in results if r["ok"]]
    summary = {"users": users, "successful": len(ok), "wall_seconds": time.perf_counter() - began,
               "errors": sorted({r["error"] for r in results if not r["ok"]})}
    if ok:
        for key in ("page_ready_s", "verdict_s"):
            values = np.array([r[key] for r in ok])
            summary[key] = {"median": float(np.median(values)), "p95": float(np.percentile(values, 95)),
                            "max": float(values.max())}
    return summary


async def main() -> None:
    """Run each requested wave sequentially and save the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, nargs="+", default=[10])
    args = parser.parse_args()
    base = os.environ.get("PRICE_TRUTH_URL", "http://127.0.0.1:8501").rstrip("/")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        waves = []
        for users in args.users:
            waves.append(await wave(browser, base, users))
            print(json.dumps(waves[-1], indent=2))
        await browser.close()
    hosted = not base.startswith(("http://127.0.0.1", "http://localhost"))
    result = {"generated_at": datetime.now(UTC).isoformat(), "url": base, "waves": waves,
              "scope": "Simultaneous headless browser sessions from one client machine; client CPU and network "
                       "also limit results. Each user opens the dashboard and waits for the analysed default "
                       "product (model, SHAP, discount check and offers)."}
    name = "load_test_hosted.json" if hosted else "load_test_local.json"
    (REPORTS / "current" / name).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
