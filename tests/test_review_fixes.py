"""Regression tests for the October 2026 code-review findings."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from price_truth import synthetic
from price_truth.market_ui import quote_history
from price_truth.paths import ROOT


def app(page):
    """Open one page offline through the real navigation."""
    test = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    test.session_state["food_offline"] = True
    return test.run().switch_page(page).run()


def test_new_search_resets_the_selected_row():
    """Finding 1: narrowing the product list never keeps a selection from the previous list."""
    page = app("views/dashboard.py")
    first = page.selectbox(key="dash_product").value
    page.text_input(key="dash_filter").set_value("boAt").run()
    assert not page.exception
    assert page.selectbox(key="dash_product").value != first
    heading = next(str(h.proto.body) for h in page.get("html") if "Selected product" in str(h.proto.body))
    assert "boat" in heading.lower()


def test_quote_replaces_todays_row_in_the_reference_window():
    """Finding 2: today's own simulated price is not part of today's 30-day reference."""
    days = pd.date_range("2025-01-01", periods=40)
    history = pd.DataFrame({"date": days, "price": [500.] * 39 + [400.], "mrp": [1000.] * 40, "event": ""})
    frame = quote_history(history, 400., 1000.)
    assert len(frame) == len(history) and frame.price.iloc[-1] == 400.
    check = synthetic.reference_check(frame, 400., 1000.)
    assert check["lowest_30d"] == 500. and check["real_discount_pct"] == pytest.approx(20)


def test_empty_food_search_shows_no_matches():
    """Finding 4: a search that finds nothing must not fall back to the default product list."""
    page = app("views/food.py")
    page.session_state["workspace_food_candidates"] = []
    page.run()
    assert not page.exception
    assert "No matching products" in " ".join(str(h.proto.body) for h in page.get("html"))


def test_price_collection_reads_files_once(monkeypatch):
    """Finding 8: repeated reruns reuse the cached collection instead of re-reading the archive."""
    from price_truth import workspace

    reads = []
    original = workspace.accumulated_observations
    monkeypatch.setattr(workspace, "accumulated_observations", lambda d: reads.append(d) or original(d))
    workspace.price_collection.clear()
    first, second = workspace.price_collection(), workspace.price_collection()
    assert len(reads) == 1 and first[1] == second[1] and len(first[0]) == len(second[0])


def test_pdf_is_built_only_on_download(monkeypatch):
    """Finding 9: rendering the result does not generate the PDF."""
    calls = []
    import price_truth.dashboard as dashboard

    monkeypatch.setattr(dashboard, "assessment_pdf", lambda *a: calls.append(1) or b"%PDF-")
    page = app("views/dashboard.py")
    assert not page.exception and page.get("download_button") and calls == []


def test_warmup_reuses_cached_objects(monkeypatch):
    """Finding 10: the warm-up thread receives the cached catalogue and model instead of loading copies."""
    from price_truth import resources

    loads = []
    monkeypatch.setattr(resources, "load_catalogue", lambda: loads.append("catalogue"))
    monkeypatch.setattr(resources, "load_model", lambda: loads.append("model"))
    frame = pd.DataFrame([{"key": "x"}])
    resources._warm(frame, {})  # fails quietly on the dummy bundle, but must not load anything
    assert loads == []
