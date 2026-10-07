"""Verify local UI flows in an isolated Chrome profile and save browser evidence."""
import json
import time

from playwright.sync_api import sync_playwright

from price_truth.paths import REPORTS


def main() -> None:
    """Measure actual visible load and check functional pages at two viewport sizes."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        start = time.perf_counter()
        page.goto("http://127.0.0.1:8501")
        page.get_by_role("heading", name="Know what your price means").wait_for()
        load_time = time.perf_counter() - start
        page.screenshot(path=str(REPORTS / "overview-desktop.png"), full_page=True)
        page.get_by_text("Discount Checker", exact=True).click()
        page.get_by_role("heading", name="True Discount Checker").wait_for()
        page.get_by_role("button", name="Assess price", exact=True).click()
        page.get_by_text("Advertised discount", exact=True).wait_for()
        page.get_by_text("Why the model estimated this price", exact=True).wait_for()
        page.screenshot(path=str(REPORTS / "checker-desktop.png"), full_page=True)
        page.get_by_text("Platform Catalogue", exact=True).first.click()
        page.get_by_role("textbox", name="Search product names", exact=True).fill("cable")
        page.get_by_role("textbox", name="Search product names", exact=True).press("Enter")
        page.get_by_role("button", name="Download results CSV").wait_for()
        page.set_viewport_size({"width": 390, "height": 844})
        # A resize retains the desktop sidebar state; close it as a mobile user would.
        close_sidebar = page.get_by_role("button", name="Collapse sidebar")
        if close_sidebar.count():
            close_sidebar.click()
        else:
            close_sidebar = page.get_by_role("button", name="Close sidebar")
            if close_sidebar.count():
                close_sidebar.click()
        page.wait_for_function("document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right <= 1")
        page.screenshot(path=str(REPORTS / "catalogue-mobile.png"), full_page=True)
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        (REPORTS / "browser_check.json").write_text(json.dumps({
            "browser": browser.version, "desktop_viewport": [1440, 1000], "mobile_viewport": [390, 844],
            "initial_visible_load_seconds": load_time, "javascript_errors": errors,
            "mobile_horizontal_page_overflow": overflow,
            "flows": ["overview rendered", "discount + SHAP rendered", "catalogue search + export visible"],
            "scope": "Local Chrome only; mobile viewport emulation, not a physical-device or cross-browser certification."
        }, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
