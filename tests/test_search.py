"""Live-search schema and honest cached fallback using retrieved product records."""
import json

import pytest
import requests

from price_truth import external


def test_real_saved_name_search():
    """A downloaded search is usable offline and carries attribution."""
    result = external.search_products("Maggi", offline=True)
    assert result["mode"] == "cached"
    assert result["products"] and result["source_url"].startswith("https://search.openfoodfacts.org")


@pytest.mark.parametrize("query", ["", "x", "x" * 101])
def test_invalid_search(query):
    """Bound query size before network use."""
    with pytest.raises(ValueError):
        external.search_products(query)


def test_search_success_and_timeout(monkeypatch, tmp_path):
    """Use retrieved hits as the response fixture and then simulate an outage."""
    saved = external.search_products("Maggi", offline=True)
    monkeypatch.setattr(external, "EXTERNAL", tmp_path)
    monkeypatch.setattr(external, "get_json", lambda *a, **k: {"hits": saved["products"]})
    result = external.search_products("Maggi")
    assert result["mode"] == "live" and len(result["products"]) == len(saved["products"])
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(external, "get_json", timeout)
    assert external.search_products("Maggi")["mode"] == "cached"
    with pytest.raises(ValueError, match="unavailable"):
        external.search_products("unknown query")
    cache = next((tmp_path / "search").glob("*.json"))
    assert json.loads(cache.read_text())["query"] == "Maggi"


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload, error=None):
        self.payload, self.error = payload, error
        self.status_code = 500 if error else 200

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_get_json_is_bounded_and_rejects_non_objects(monkeypatch):
    """Requests carry the identifying header and timeout; only JSON objects are accepted."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(external.requests, "get", fake_get)
    assert external.get_json("https://example.com/api", {"q": 1}) == {"ok": True}
    assert calls == [("https://example.com/api", {"params": {"q": 1}, "headers": external.HEADERS,
                                                  "timeout": (5, 15)})]
    monkeypatch.setattr(external.requests, "get", lambda *a, **k: FakeResponse([1, 2]))
    with pytest.raises(ValueError, match="unexpected response"):
        external.get_json("https://example.com/api")
    monkeypatch.setattr(external.requests, "get",
                        lambda *a, **k: FakeResponse({}, requests.HTTPError("500")))
    with pytest.raises(requests.HTTPError):
        external.get_json("https://example.com/api")


def test_search_requests_and_filters_hits(monkeypatch, tmp_path):
    """Only barcode-like hits are kept, with the English name preferred."""
    calls = []

    def fake(url, params):
        calls.append((url, params))
        return {"hits": [{"code": "12345678", "product_name_en": "English", "product_name": "Local",
                          "brands": "B", "quantity": "1 kg"},
                         {"code": "1234", "product_name": "Too short"},
                         {"product_name": "No code"},
                         {"code": "87654321", "product_name": "Local only"}]}

    monkeypatch.setattr(external, "EXTERNAL", tmp_path)
    monkeypatch.setattr(external, "get_json", fake)
    result = external.search_products("  Rice  ")
    assert calls == [("https://search.openfoodfacts.org/search", {"q": "Rice", "page_size": 10})]
    assert result["products"] == [
        {"code": "12345678", "product_name": "English", "brands": "B", "quantity": "1 kg"},
        {"code": "87654321", "product_name": "Local only", "brands": None, "quantity": None}]
    assert result["query"] == "Rice" and result["license"] == "ODbL" and result["mode"] == "live"
    again = external.search_products("rice")
    assert again["mode"] == "cached" and again["products"] == result["products"]


def test_search_rejects_malformed_hits_and_missing_offline_cache(monkeypatch, tmp_path):
    """A non-list hits field is an outage; offline search needs a saved response."""
    monkeypatch.setattr(external, "EXTERNAL", tmp_path)
    monkeypatch.setattr(external, "get_json", lambda *a: {"hits": "nope"})
    with pytest.raises(ValueError, match="Live search is unavailable"):
        external.search_products("Rice")
    with pytest.raises(ValueError, match="No saved results for this search"):
        external.search_products("Rice", offline=True)


def test_search_outage_falls_back_to_stale_saved_results(monkeypatch, tmp_path):
    """An expired saved search is still shown, marked cached, when the live search fails."""
    saved = external.search_products("Maggi", offline=True)
    monkeypatch.setattr(external, "EXTERNAL", tmp_path)
    monkeypatch.setattr(external, "get_json", lambda *a: {"hits": saved["products"]})
    external.search_products("Maggi")
    cache = next((tmp_path / "search").glob("*.json"))
    stale = {**json.loads(cache.read_text()), "fetched_at": "2020-01-01T00:00:00+00:00"}
    cache.write_text(json.dumps(stale))
    monkeypatch.setattr(external, "get_json", lambda *a: {})
    result = external.search_products("Maggi")
    assert result["mode"] == "cached" and result["fetched_at"] == "2020-01-01T00:00:00+00:00"


def test_fresh_lookup_cache_is_reused(monkeypatch, tmp_path):
    """A response saved within the hour is served without a new request."""
    monkeypatch.setattr(external, "get_json",
                        lambda *a, **k: {"status": 1, "product": {"code": "12345678"}})
    assert external.lookup_product("12345678", cache_dir=tmp_path)["mode"] == "live"
    monkeypatch.setattr(external, "get_json", lambda *a, **k: pytest.fail("network used"))
    result = external.lookup_product(" 12345678 ", cache_dir=tmp_path)
    assert result["mode"] == "cached"
    assert result["notice"] == "Recently retrieved response (one-hour cache)."

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(external, "get_json", timeout)
    with pytest.raises(ValueError, match="no cached record"):
        external.lookup_product("87654321", cache_dir=tmp_path)


def test_failed_cache_write_keeps_previous_entry(tmp_path):
    """A value that cannot be serialized leaves the old entry and no temporary file."""
    from price_truth.cache import read_json, write_json
    path = tmp_path / "entry.json"
    write_json(path, {"old": 1})
    with pytest.raises(TypeError):
        write_json(path, {"bad": object()})
    assert read_json(path) == {"old": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["entry.json"]
    path.write_text("[1, 2]")
    assert read_json(path) is None


def test_api_calls_are_logged_as_structured_events(monkeypatch, caplog):
    """Each public API call logs its host, status and duration; failures log the error type."""
    import logging

    import requests

    from price_truth import external

    # The app's JSON handler stops propagation; let pytest's capture see the records too.
    monkeypatch.setattr(logging.getLogger("price_truth"), "propagate", True)
    monkeypatch.setattr(external.requests, "get", lambda *a, **k: FakeResponse({"ok": 1}))
    with caplog.at_level(logging.INFO, logger="price_truth.external"):
        external.get_json("https://world.openfoodfacts.org/api/v2/product/1")
    record = caplog.records[-1]
    assert record.event == "api_request" and record.host == "world.openfoodfacts.org" and record.status == 200
    assert record.duration_ms >= 0

    def fail(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(external.requests, "get", fail)
    with caplog.at_level(logging.INFO, logger="price_truth.external"), pytest.raises(requests.Timeout):
        external.get_json("https://prices.openfoodfacts.org/api/v1/prices")
    assert caplog.records[-1].event == "api_error" and caplog.records[-1].error == "Timeout"
