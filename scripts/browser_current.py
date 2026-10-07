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


def visit(page, base: str, path: str, heading: str) -> None:
    """Open one page by URL and wait for its heading."""
    page.goto(f"{base}/{path}")
    page.get_by_role("heading", name=heading).first.wait_for(timeout=60_000)


def check_price(page, base: str, out: Path) -> None:
    """Real model flow: verdict, charts and an actual PDF download."""
    visit(page, base, "product", "Is this a good price?")
    page.get_by_role("button", name="Check this price", exact=True).click()
    page.get_by_text("Advertised discount", exact=True).first.wait_for(timeout=60_000)
    page.get_by_text("What moved the estimate").first.wait_for()
    download = page.get_by_role("button", name="Download PDF report", exact=True)
    page.screenshot(path=str(out / "workspace-desktop.png"), full_page=True)
    with page.expect_download() as pending:
        download.click()
    pending.value.save_as(str(out / "browser-assessment.pdf"))
    assert (out / "browser-assessment.pdf").read_bytes().startswith(b"%PDF-")


def check_unit(page, base: str) -> None:
    """Unit comparison with typed values produces a best-value verdict."""
    visit(page, base, "compare", "Which pack is better value?")
    for label, value in [("Price (INR)", "10"), ("Quantity per pack", "100")]:
        fields = page.get_by_label(label)
        fields.nth(0).fill(value)
        fields.nth(1).fill(str(float(value) * (1.5 if label.startswith("Price") else 2)))
    page.get_by_role("button", name="Compare value").click()
    page.get_by_text("Option 2 is the best value").wait_for(timeout=30_000)


def check_food_and_shrink(page, base: str) -> None:
    """Saved food data and the documented shrinkflation case render."""
    visit(page, base, "food", "Look up a food pack")
    page.get_by_text("Saved responses only").click()
    page.get_by_text("Pack size:").first.wait_for(timeout=30_000)
    visit(page, base, "shrink", "Same price, smaller pack")
    page.get_by_text("Hidden price increase").wait_for()


def accessibility(page, base: str) -> list:
    """Run axe-core on each page; report serious and critical WCAG A/AA violations."""
    found = []
    for path, heading in [("", "Know what a price really means"), ("product", "Is this a good price?"),
                          ("compare", "Which pack is better value?"), ("methods", "Methods, data and limits")]:
        visit(page, base, path, heading)
        page.wait_for_timeout(800)
        page.add_script_tag(url=AXE)
        report = page.evaluate("axe.run(document, {runOnly: ['wcag2a', 'wcag2aa']})")
        found += [{"page": path or "home", "rule": v["id"], "impact": v["impact"], "nodes": len(v["nodes"])}
                  for v in report["violations"] if v["impact"] in ("serious", "critical")]
    return found


def check_viewports(page, base: str, out: Path) -> list:
    """Measure horizontal overflow at three viewports; emulation is not a physical-device test."""
    results = []
    visit(page, base, "product", "Is this a good price?")
    for width, height in [(1440, 1000), (768, 1024), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(500)
        page.screenshot(path=str(out / f"workspace-{width}.png"), full_page=True)
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        results.append({"width": width, "height": height, "horizontal_page_overflow": overflow})
    return results


def main() -> None:
    """Exercise the app in one browser engine and save the evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=["chrome", "firefox", "webkit"], default="chrome")
    args = parser.parse_args()
    base = os.environ.get("PRICE_TRUTH_URL", "http://127.0.0.1:8501").rstrip("/")
    hosted = not base.startswith(("http://127.0.0.1", "http://localhost"))
    out = (OUT / "hosted" if hosted else OUT) / ("" if args.browser == "chrome" else args.browser)
    out.mkdir(parents=True, exist_ok=True)
    mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    executable = os.environ.get("PRICE_TRUTH_CHROME") or (mac_chrome if Path(mac_chrome).exists() else None)
    with sync_playwright() as playwright:
        engine = playwright.chromium if args.browser == "chrome" else getattr(playwright, args.browser)
        browser = engine.launch(executable_path=executable if args.browser == "chrome" else None, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        start = time.perf_counter()
        visit(page, base, "", "Know what a price really means")
        load_seconds = time.perf_counter() - start
        check_price(page, base, out)
        check_unit(page, base)
        check_food_and_shrink(page, base)
        violations = accessibility(page, base) if args.browser == "chrome" else None
        viewports = check_viewports(page, base, out)
        result = {"generated_at": datetime.now(UTC).isoformat(), "url": base, "browser": browser.version,
                  "engine": args.browser, "initial_visible_load_seconds": load_seconds,
                  "javascript_errors": errors, "viewports": viewports,
                  "accessibility_serious_or_critical": violations,
                  "flows": ["home", "price check with real model and PDF download", "unit comparison",
                            "offline food lookup", "shrinkflation case"],
                  "scope": f"{'Hosted' if hosted else 'Local'} {args.browser}; three viewport emulations. "
                           "WebKit is not branded Safari; emulation is not a physical device."}
        (out / "browser_check.json").write_text(json.dumps(result, indent=2))
        browser.close()
        assert not errors and not any(v["horizontal_page_overflow"] for v in viewports), result
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
