"""API degradation, safe exports, and time-series correctness."""
import json
from datetime import date, timedelta

import pandas as pd
import pytest
import requests

from price_truth import external
from price_truth.catalogue import export_csv, safe_url, search
from price_truth.history import load_observations, series_for, timing_signal


@pytest.mark.parametrize("code", ["abc", "../../secret", "123", "1" * 15])
def test_invalid_barcode_never_calls_network(code, monkeypatch, tmp_path):
    """A barcode must not become an arbitrary path or URL."""
    monkeypatch.setattr(external, "get_json", lambda *_: pytest.fail("Network must not be used"))
    with pytest.raises(ValueError):
        external.lookup_product(code, cache_dir=tmp_path)


def test_offline_and_timeout_use_real_cache(monkeypatch, tmp_path):
    """A failed request returns a clearly marked, previously retrieved record."""
    source = next((external.EXTERNAL / "off").glob("*.json"))
    record = json.loads(source.read_text())
    record["fetched_at"] = "2025-01-01T00:00:00+00:00"  # older than the one-hour cache, so a live call is tried
    (tmp_path / source.name).write_text(json.dumps(record))
    code = source.stem
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(external, "get_json", timeout)
    assert external.lookup_product(code, True, tmp_path)["mode"] == "cached"
    result = external.lookup_product(code, False, tmp_path)
    assert "unavailable" in result["notice"]
    assert result["product"] == json.loads(source.read_text())["product"]


def test_not_found_and_missing_cache(monkeypatch, tmp_path):
    """Unavailable barcodes produce explicit errors, not fabricated products."""
    with pytest.raises(ValueError, match="offline cache"):
        external.lookup_product("12345678", True, tmp_path)
    monkeypatch.setattr(external, "get_json", lambda *a, **k: {"status": 0})
    with pytest.raises(ValueError, match="No product"):
        external.lookup_product("12345678", False, tmp_path)


def test_success_saves_real_response(monkeypatch, tmp_path):
    """Use an actual downloaded response as the deterministic integration fixture."""
    source = next((external.EXTERNAL / "off").glob("*.json"))
    record = json.loads(source.read_text())
    monkeypatch.setattr(external, "get_json", lambda *a, **k: {"status": 1, "product": record["product"]})
    result = external.lookup_product(source.stem, cache_dir=tmp_path)
    assert result["mode"] == "live"
    assert (tmp_path / source.name).exists()


def test_literal_search_and_empty_platforms():
    """User punctuation is literal; deselecting all platforms returns no products."""
    frame = pd.DataFrame({"name": ["Cable [USB]", "Cable lightning"], "platform": ["amazon", "flipkart"]})
    assert len(search(frame, "[USB]")) == 1
    assert search(frame, "Cable", []).empty


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://evil.test/", "https://www.amazon.in.evil.test/x"])
def test_reject_unsafe_links(url):
    """Only the two original retail hosts are permitted."""
    assert safe_url(url) is None


def test_safe_link_and_export():
    """Keep genuine links and neutralize spreadsheet formulas in source text."""
    assert safe_url("https://www.amazon.in/dp/B07JW9H4J1")
    result = export_csv(pd.DataFrame({"name": ["=1+1", " @SUM(A1)", "Cable"], "price": [1, 2, 3]})).decode("utf-8-sig")
    assert "'=1+1" in result and "' @SUM" in result


def test_real_history_stays_in_one_store_currency_and_product():
    """No apparent price trend may be created by mixing shops or currencies."""
    frame, _ = load_observations()
    row = frame[(frame.product_code == "8901030795589") & (frame.location_id == 2754)].iloc[0]
    series = series_for(frame, row.product_code, row.location_id, row.currency, "UNKNOWN")
    assert len(series) == 2
    assert (series.price > 0).all()
    assert series.date.is_unique
    assert series_for(frame, row.product_code, row.location_id, "USD", "UNKNOWN").empty


def test_history_default_unit_matches_explicit_unit():
    """Default callers must select UNIT, not unknown or changed price bases."""
    frame, _ = load_observations()
    row = frame.iloc[0].to_dict()
    row.update(product_code="12345678", location_id=1, currency="INR", price_per="UNIT",
               duplicate_of=None, proof_id=1, location_type="shop", price=10, date="2026-01-01")
    fixture = pd.DataFrame([row, {**row, "price_per": "KG", "price": 200}])
    result = series_for(fixture, "12345678", 1, "INR")
    assert result.price.tolist() == [10]
    pd.testing.assert_frame_equal(result, series_for(fixture, "12345678", 1, "INR", "UNIT"))


def test_history_filters_incompatible_or_unproven_observations():
    """Boundary records derived from one real observation must not contaminate a series."""
    frame, _ = load_observations()
    row = frame[(frame.product_code == "8901030795589") & (frame.location_id == 2754)].iloc[0]
    original = row.to_dict()
    records = [original]
    for changed in [{"currency": "EUR"}, {"location_id": -1}, {"product_code": "12345678"},
                    {"price_per": "KILOGRAM"}, {"duplicate_of": 1}, {"proof_id": None},
                    {"location_type": "boundary"}, {"date": "2099-01-01"},
                    {"date": "invalid"}, {"price": -1}]:
        records.append({**original, "price": 99999, **changed})
    series = series_for(pd.DataFrame(records), row.product_code, row.location_id, "INR", "UNKNOWN")
    assert len(series) == 1
    assert series.iloc[0].price == row.price
    assert series.iloc[0].observations == 1


def test_history_same_day_median_and_sorting():
    """Repeated receipts on one date contribute one day, not extra historical coverage."""
    frame, _ = load_observations()
    row = frame[(frame.product_code == "8901030795589") & (frame.location_id == 2754)].iloc[0].to_dict()
    records = [{**row, "date": "2026-01-02", "price": 10},
               {**row, "date": "2026-01-01", "price": 20},
               {**row, "date": "2026-01-02", "price": 30}]
    result = series_for(pd.DataFrame(records), row["product_code"], row["location_id"], "INR", "UNKNOWN")
    assert result.price.tolist() == [20, 20]
    assert result.observations.tolist() == [1, 2]


def test_search_multiple_words_case_and_platform():
    """All literal words and the selected platform are required."""
    frame = pd.DataFrame({"name": ["USB Cable", "USB Plug", "Cable usb", None],
                          "platform": ["amazon", "amazon", "flipkart", "amazon"]})
    assert search(frame, "  usb cable  ", ["amazon"]).index.tolist() == [0]
    assert len(search(frame, "", ["flipkart"])) == 1


@pytest.mark.parametrize("unit,currency", [("UNIT", "EUR"), ("UNKNOWN", "INR")])
def test_collection_selection_and_metadata(unit, currency):
    """The international example stays separate and source metadata is retained."""
    frame, meta = load_observations(example=currency == "EUR")
    assert set(frame.currency) == {currency}
    assert "observations" not in meta
    assert meta["license"] == "ODbL-1.0"


def test_history_sparse_stale_and_future():
    """Boundary fixtures test abstention; they are never training observations."""
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-10", "2026-02-01",
                                                "2026-02-10", "2026-03-01", "2099-01-01"]),
                          "price": [10, 11, 12, 13, 14, 9999]})
    assert timing_signal(frame.iloc[:2], 12)["status"] == "insufficient_history"
    assert timing_signal(frame, 12, date(2026, 9, 19))["status"] == "limited_history"
    result = timing_signal(frame, 8, date(2026, 3, 2))
    assert result["status"] == "below_usual"
    assert result["median"] == 12
    assert result["days"] == 5


@pytest.mark.parametrize("quote,status", [(8, "below_usual"), (20, "above_usual"),
                                         (11, "within_usual"), (13, "within_usual")])
def test_timing_quartile_boundaries(quote, status):
    """Quartile boundaries are included in the usual range."""
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-08",
                                                "2026-01-10", "2026-01-15"]),
                          "price": [10, 11, 12, 13, 14]})
    result = timing_signal(frame, quote, date(2026, 1, 16))
    assert result["status"] == status
    assert result["q25"] == 11 and result["q75"] == 13
    assert result["difference_from_median_pct"] == pytest.approx(100 * (quote / 12 - 1))
    assert result["age_days"] == 1 and result["span_days"] == 14


def test_timing_same_day_quote_excluded_and_short_span():
    """The current quote cannot count as prior evidence."""
    frame = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=5), "price": [10, 11, 12, 13, 14]})
    assert timing_signal(frame, 12, date(2026, 1, 5))["status"] == "insufficient_history"
    assert timing_signal(frame, 12, date(2026, 1, 6))["status"] == "limited_history"
    with pytest.raises(ValueError):
        timing_signal(frame, 0)


def test_history_includes_today_but_excludes_zero_prices():
    """Fresh observations belong in history; a free/invalid quote cannot lower the median."""
    frame, _ = load_observations()
    row = frame.iloc[0].to_dict()
    row.update(product_code="12345678", location_id=1, currency="INR", price_per="UNIT",
               duplicate_of=None, proof_id=1, location_type="shop", date=date.today().isoformat(), price=10)
    result = series_for(pd.DataFrame([row, {**row, "price": 0}]), "12345678", 1, "INR")
    assert result.price.tolist() == [10] and result.observations.tolist() == [1]


@pytest.mark.parametrize("age,status", [(90, "within_usual"), (91, "limited_history")])
def test_history_freshness_exact_boundary(age, status):
    """The stated 90-day limit includes day 90 and excludes day 91."""
    end = date(2026, 5, 1)
    frame = pd.DataFrame({"date": pd.date_range(end=end, periods=5, freq="7D"), "price": [10]*5})
    assert timing_signal(frame, 10, end+timedelta(days=age))["status"] == status


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t=", "\r+"])
def test_export_neutralizes_spreadsheet_formula_prefixes(prefix):
    """External text cannot become a formula when the exported CSV is opened."""
    import io
    value = prefix+"SUM(A1)"
    exported = pd.read_csv(io.BytesIO(export_csv(pd.DataFrame({"text": [value]}))))
    assert exported.text.iloc[0] == "'"+value


@pytest.mark.parametrize("url", ["https://user:password@www.amazon.in/x", "https://[bad", None,
                                 "https://www.amazon.in/x\nignored"])
def test_malformed_and_credential_links_are_not_exposed(url):
    """Invalid source links should neither crash the UI nor expose embedded credentials."""
    assert safe_url(url) is None


@pytest.mark.parametrize("url", ["https://www.flipkart.com/a", "http://www.flipkart.com/a",
                                 "https://www.amazon.in/a", "http://www.amazon.in/a"])
def test_both_source_retailer_links_remain_available(url):
    """Both original retailer domains can be opened for source inspection."""
    assert safe_url(url) == url


@pytest.mark.parametrize("url", ["https://user@www.amazon.in/x", "https://:pw@www.amazon.in/x"])
def test_username_or_password_alone_is_rejected(url):
    """Either credential component on its own blocks the link."""
    assert safe_url(url) is None


def test_export_exact_bytes_leave_safe_values_untouched():
    """Only formula-like text is prefixed; other values, the BOM and CRLF rows are exact."""
    frame = pd.DataFrame({"name": ["=1", "Cable", None, 5], "price": [1, 2, 3, 4]})
    assert export_csv(frame) == "﻿name,price\r\n'=1,1\r\nCable,2\r\n,3\r\n5,4\r\n".encode()


def test_history_reads_the_documented_files(monkeypatch):
    """The INR collection and the international example are read by their exact file names."""
    from price_truth import history
    requested, real = [], history.EXTERNAL

    class Recorder:
        """Record file names joined to the data directory (case-insensitive file systems
        would otherwise hide a wrongly cased name)."""

        def __truediv__(self, name):
            requested.append(name)
            return real / name

    monkeypatch.setattr(history, "EXTERNAL", Recorder())
    load_observations()
    load_observations(example=True)
    assert requested == ["open_prices_inr.json", "open_prices_example.json"]


def test_history_keeps_prices_below_one():
    """Any positive price, including fractions of a currency unit, is a valid observation."""
    frame, _ = load_observations()
    row = frame.iloc[0].to_dict()
    row.update(product_code="12345678", location_id=1, currency="INR", price_per="UNIT",
               duplicate_of=None, proof_id=1, location_type="shop", price=0.5, date="2026-01-01")
    assert series_for(pd.DataFrame([row]), "12345678", 1, "INR").price.tolist() == [0.5]


def test_timing_signal_result_keys_and_messages():
    """Each outcome carries its documented explanation."""
    dates = pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-08", "2026-01-10", "2026-01-15"])
    frame = pd.DataFrame({"date": dates, "price": [10, 11, 12, 13, 14]})
    assert timing_signal(frame.iloc[:2], 12, date(2026, 1, 16)) == {
        "status": "insufficient_history", "days": 2,
        "message": "At least five distinct prior observation dates are needed."}
    limited = timing_signal(frame, 12, date(2026, 6, 1))
    assert limited["message"] == "History is stale or spans fewer than 14 days; no buy/wait signal."
    usual = timing_signal(frame, 12, date(2026, 1, 16))
    assert usual["message"] == ("Comparison with observed prices only. Future prices and sale "
                                "dates are unknown.")
    assert set(usual) == {"days", "span_days", "age_days", "median", "q25", "q75",
                          "difference_from_median_pct", "status", "message"}


def test_unknown_barcode_is_reported_as_not_found(monkeypatch, tmp_path):
    """A 404 from Open Food Facts means the product is unknown, not that the service is down."""
    response = requests.Response()
    response.status_code = 404

    def not_found(*args, **kwargs):
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(external, "get_json", not_found)
    with pytest.raises(ValueError, match="No product found"):
        external.lookup_product("12345678", False, tmp_path)
    response.status_code = 503
    with pytest.raises(ValueError, match="unavailable"):
        external.lookup_product("12345678", False, tmp_path)
