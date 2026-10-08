"""Browser workflow, viewport and accessibility checks with retained evidence.

PRICE_TRUTH_URL selects the app (default local). For Streamlit Community Cloud use the
app's inner URL, e.g. https://<name>.streamlit.app/~/+  (the outer page is an iframe wrapper).
"""
import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from price_truth.paths import REPORTS

OUT = REPORTS / "current"
AXE = "https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js"
DASHBOARD = "Is this a fair price?"
LANDING = "Is your discount actually real?"
# Browser notices that are not application errors; recorded separately, never dropped.
BENIGN = ("ResizeObserver loop completed with undelivered notifications",  # layout notice (Plotly/Streamlit)
          "due to access control checks")  # WebKit's wording when navigation cancels a pending media fetch


def split_messages(messages: list[str]) -> tuple[list[str], list[str]]:
    """Separate application errors from known benign browser notices."""
    benign = [m for m in messages if any(b in m for b in BENIGN)]
    return [m for m in messages if m not in benign], benign


def visit(page, base: str, path: str, heading: str) -> None:
    """Open one page by URL and wait for its heading."""
    page.goto(f"{base}/{path}")
    page.get_by_role("heading", name=heading).first.wait_for(timeout=90_000)


def check_landing(page, base: str) -> None:
    """The landing page loads and its search opens the dashboard filtered to the query."""
    visit(page, base, "", LANDING)
    page.get_by_placeholder("Try").fill("cable")
    page.get_by_role("button", name="Check price").click()
    page.get_by_role("heading", name=DASHBOARD).wait_for(timeout=90_000)
    page.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)


def check_dashboard(page, base: str, out: Path) -> None:
    """Default product analysed with the real model: headline cards, explanation and a real PDF download."""
    visit(page, base, "dashboard", DASHBOARD)
    page.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)
    page.get_by_text("What moved the estimate").first.wait_for(timeout=60_000)
    page.get_by_role("link", name="Where to buy").click()
    page.get_by_text("Cheapest platform today").wait_for()
    page.screenshot(path=str(out / "workspace-desktop.png"), full_page=True)
    with page.expect_download() as pending:
        page.get_by_role("button", name="Download PDF report", exact=True).click()
    pending.value.save_as(str(out / "browser-assessment.pdf"))
    if not (out / "browser-assessment.pdf").read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("The downloaded assessment is not a PDF.")


def check_unit(page) -> None:
    """Unit comparison on the dashboard with typed values produces a best-value verdict."""
    page.get_by_role("link", name="Pack value").click()
    for label, value in [("Price (INR)", "10"), ("Quantity per pack", "100")]:
        fields = page.get_by_label(label)
        fields.nth(0).fill(value)
        fields.nth(1).fill(str(float(value) * (1.5 if label.startswith("Price") else 2)))
    page.get_by_role("button", name="Compare value").click()
    page.get_by_text("Option 2 is the best value").wait_for(timeout=30_000)
    page.get_by_text("real price per").first.wait_for()


def check_food(page, base: str) -> None:
    """Saved food data renders offline."""
    visit(page, base, "food", "Look up a food pack")
    page.get_by_text("Saved responses only").click()
    page.get_by_text("Pack size:").first.wait_for(timeout=30_000)


def accessibility(page, base: str) -> list:
    """Run axe-core on each page; report serious and critical WCAG A/AA violations."""
    found = []
    for path, heading in [("", LANDING), ("dashboard", DASHBOARD), ("food", "Look up a food pack"),
                          ("methods", "Methods, data and limits")]:
        visit(page, base, path, heading)
        page.wait_for_timeout(1500)
        page.add_script_tag(url=AXE)
        report = page.evaluate("axe.run(document, {runOnly: ['wcag2a', 'wcag2aa']})")
        found += [{"page": path or "home", "rule": v["id"], "impact": v["impact"], "nodes": len(v["nodes"])}
                  for v in report["violations"] if v["impact"] in ("serious", "critical")]
    return found


def check_viewports(page, base: str, out: Path) -> list:
    """Measure horizontal overflow at three viewports; emulation is not a physical-device test."""
    results = []
    visit(page, base, "dashboard", DASHBOARD)
    page.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)
    for width, height in [(1440, 1000), (768, 1024), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(800)
        page.screenshot(path=str(out / f"workspace-{width}.png"), full_page=True)
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        results.append({"width": width, "height": height, "horizontal_page_overflow": overflow})
    return results


def launch(playwright, engine: str):
    """Start the requested engine; Chrome uses an installed browser when one is configured or found."""
    if engine != "chrome":
        return getattr(playwright, engine).launch(headless=True)
    mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    executable = os.environ.get("PRICE_TRUTH_CHROME") or (mac_chrome if Path(mac_chrome).exists() else None)
    return playwright.chromium.launch(executable_path=executable, headless=True)


def run_flows(page, base: str, out: Path, engine: str) -> dict:
    """Every user flow, timed from the first request to the first analysed dashboard."""
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    start = time.perf_counter()
    visit(page, base, "dashboard", DASHBOARD)
    page.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)
    load_seconds = time.perf_counter() - start
    check_landing(page, base)
    check_dashboard(page, base, out)
    check_unit(page)
    check_food(page, base)
    violations = accessibility(page, base) if engine == "chrome" else None
    errors, benign = split_messages(errors)
    return {"initial_analysed_dashboard_seconds": load_seconds, "javascript_errors": errors,
            "benign_browser_notices": benign,
            "viewports": check_viewports(page, base, out), "accessibility_serious_or_critical": violations}


def main() -> None:
    """Exercise the app in one browser engine and save the evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=["chrome", "firefox", "webkit"], default="chrome")
    args = parser.parse_args()
    base = os.environ.get("PRICE_TRUTH_URL", "http://127.0.0.1:8501").rstrip("/")
    hosted = not base.startswith(("http://127.0.0.1", "http://localhost"))
    out = (OUT / "hosted" if hosted else OUT) / ("" if args.browser == "chrome" else args.browser)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = launch(playwright, args.browser)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        result = {"generated_at": datetime.now(UTC).isoformat(), "url": base, "browser": browser.version,
                  "engine": args.browser, **run_flows(page, base, out, args.browser),
                  "flows": ["landing page search into the dashboard", "dashboard with real model, section navigation and PDF download",
                            "unit comparison on the dashboard", "shrinkflation case", "offline food lookup"],
                  "scope": f"{'Hosted' if hosted else 'Local'} {args.browser}; three viewport emulations. "
                           "WebKit is not branded Safari; emulation is not a physical device."}
        (out / "browser_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        browser.close()
    if result["javascript_errors"] or any(v["horizontal_page_overflow"] for v in result["viewports"]):
        raise SystemExit(f"Browser check failed: {result}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
