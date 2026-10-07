"""Open Prices client contracts with a stubbed network and test-only payloads."""
from datetime import UTC, date, datetime, timedelta

import pytest
import requests

from price_truth import price_api
from price_truth.cache import read_json, write_json

CODE = "00001234"


def item(**changes) -> dict:
    """A test-only provider item, including contributor fields that must be discarded."""
    base = {"id": 7, "product_code": CODE, "price": "12.5", "currency": "INR",
            "date": "2026-01-01", "product": {"product_name": "Nested name"},
            "product_name": "Flat name", "price_per": "UNIT", "price_is_discounted": True,
            "price_without_discount": 15, "location_id": 3,
            "location": {"osm_name": "Shop", "osm_tag_key": "shop", "owner": "x"},
            "proof_id": 9, "duplicate_of": 4, "owner": "secret", "proof": {"owner": "p"}}
    return {**base, **changes}


def test_normalize_maps_every_retained_field():
    """Only documented evidence fields survive normalization."""
    assert price_api.normalize(item()) == {
        "id": 7, "product_code": CODE, "product_name": "Nested name", "price": 12.5,
        "currency": "INR", "date": "2026-01-01", "price_per": "UNIT", "price_is_discounted": True,
        "price_without_discount": 15, "location_id": 3, "location_name": "Shop",
        "location_type": "shop", "proof_id": 9, "duplicate_of": 4,
        "source_url": "https://prices.openfoodfacts.org/prices/7"}


def test_normalize_optional_fields():
    """Missing nested objects fall back to flat names or None."""
    minimal = {"id": 1, "price": 2, "currency": "EUR", "date": "2026-01-01"}
    result = price_api.normalize({**minimal, "product": None, "location": None,
                                  "product_name": "Flat"})
    assert result["product_name"] == "Flat"
    assert result["location_name"] is None and result["location_type"] is None
    assert result["product_code"] is None and result["proof_id"] is None
    result = price_api.normalize({**minimal, "product": {"product_name": ""}, "product_name": "Flat"})
    assert result["product_name"] == "Flat"
    assert price_api.normalize(minimal)["product_name"] is None


def test_normalize_accepts_today_and_rejects_bad_values():
    """Today and tomorrow (contributor-timezone skew) are valid; later dates, bad currencies and prices are not."""
    today = date.today().isoformat()
    assert price_api.normalize(item(date=today))["date"] == today
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert price_api.normalize(item(date=tomorrow))["date"] == tomorrow
    later = (date.today() + timedelta(days=2)).isoformat()
    for bad in [{"date": later}, {"currency": "inr"}, {"currency": "INRX"}]:
        with pytest.raises(ValueError, match="^Source returned an invalid date or currency.$"):
            price_api.normalize(item(**bad))
    with pytest.raises(ValueError):
        price_api.normalize(item(price=0))


def record(**changes) -> dict:
    """A schema-valid cached response for CODE."""
    base = {"source": price_api.URL, "fetched_at": datetime.now(UTC).isoformat(),
            "license": "ODbL-1.0", "total_at_source": 1, "complete_query": True,
            "observations": [price_api.normalize(item())]}
    return {**base, **changes}


def test_valid_cache_accepts_schema_valid_record():
    """A correct record for the requested barcode is valid, including an empty list."""
    assert price_api.valid_cache(record(), CODE) is True
    assert price_api.valid_cache(record(observations=[]), CODE) is True
    today = price_api.normalize(item(date=date.today().isoformat()))
    assert price_api.valid_cache(record(observations=[today]), CODE) is True


@pytest.mark.parametrize("changes", [
    {"fetched_at": "2026-01-01T00:00:00"}, {"fetched_at": "garbage"}, {"fetched_at": None},
    {"observations": {}}, {"complete_query": 1}, {"complete_query": None},
])
def test_valid_cache_rejects_bad_metadata(changes):
    """Naive timestamps, non-list rows and non-boolean completeness are rejected."""
    assert price_api.valid_cache(record(**changes), CODE) is False


@pytest.mark.parametrize("changes", [
    {"product_code": "99999999"}, {"price": 0}, {"price": "x"}, {"price": None},
    {"date": (date.today() + timedelta(days=2)).isoformat()}, {"date": "bad"},
    {"currency": "inr"}, {"currency": None},
])
def test_valid_cache_rejects_bad_rows(changes):
    """Any wrong-product or invalid row invalidates the whole cache entry."""
    good = price_api.normalize(item())
    assert price_api.valid_cache(record(observations=[good, {**good, **changes}]), CODE) is False


@pytest.mark.parametrize("key", ["fetched_at", "observations", "complete_query"])
def test_valid_cache_rejects_missing_keys(key):
    """Missing required keys make a cache invalid rather than raising."""
    data = record()
    del data[key]
    assert price_api.valid_cache(data, CODE) is False
    row = price_api.normalize(item())
    for field in ["product_code", "price", "date", "currency"]:
        partial = {k: v for k, v in row.items() if k != field}
        assert price_api.valid_cache(record(observations=[partial]), CODE) is False


@pytest.fixture
def cache_root(monkeypatch, tmp_path):
    """Redirect the price cache to an isolated directory."""
    monkeypatch.setattr(price_api, "EXTERNAL", tmp_path)
    return tmp_path / "price_cache"


def offline_network(*args, **kwargs):
    """Stand-in for a failed live request."""
    raise requests.ConnectionError("offline")


@pytest.mark.parametrize("code", ["1234567", "123456789012345", "1234567a", "../12345678", ""])
def test_barcode_is_validated_before_any_io(code, cache_root, monkeypatch):
    """Only 8-14 digit barcodes reach the cache or network."""
    monkeypatch.setattr(price_api, "get_json", lambda *a: pytest.fail("network used"))
    with pytest.raises(ValueError, match="^Enter an 8-14 digit barcode.$"):
        price_api.fetch_observations(code)


def test_live_fetch_requests_filters_and_saves(cache_root, monkeypatch):
    """The live request is bounded, keeps only this barcode, and is saved for reuse."""
    calls = []

    def fake(url, params):
        calls.append((url, params))
        return {"items": [item(), item(id=8, product_code="99999999")], "total": 2}

    monkeypatch.setattr(price_api, "get_json", fake)
    result = price_api.fetch_observations(CODE)
    assert calls == [(price_api.URL, {"product_code": CODE, "size": 100, "order_by": "-date"})]
    assert result["mode"] == "live"
    assert result["notice"] == "Live retrieval of dated observations, not a live retailer quote."
    assert result["source"] == "https://prices.openfoodfacts.org/api/v1/prices"
    assert result["license"] == "ODbL-1.0"
    assert result["total_at_source"] == 2
    assert result["complete_query"] is True
    assert [o["id"] for o in result["observations"]] == [7]
    assert datetime.fromisoformat(result["fetched_at"]).tzinfo is not None
    assert [p.name for p in cache_root.parent.iterdir()] == ["price_cache"]
    saved = read_json(cache_root / f"{CODE}.json")
    assert saved == {k: v for k, v in result.items() if k not in {"mode", "notice"}}


@pytest.mark.parametrize(("pages", "complete"), [(1, True), (0, True), (2, False)])
def test_complete_query_reflects_page_count(pages, complete, cache_root, monkeypatch):
    """Only a single page of results is a complete query."""
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": [], "pages": pages})
    assert price_api.fetch_observations(CODE)["complete_query"] is complete


def test_numeric_product_codes_are_compared_as_text(cache_root, monkeypatch):
    """Provider codes may be numbers; matching uses their text form."""
    monkeypatch.setattr(price_api, "get_json",
                        lambda *a: {"items": [item(product_code=12345678)]})
    assert len(price_api.fetch_observations("12345678")["observations"]) == 1


def test_fresh_cache_is_served_without_network(cache_root, monkeypatch):
    """A fresh valid cache answers both online and offline requests."""
    write_json(cache_root / f"{CODE}.json", record())
    monkeypatch.setattr(price_api, "get_json", lambda *a: pytest.fail("network used"))
    for offline in [False, True]:
        result = price_api.fetch_observations(CODE, offline=offline)
        assert result["mode"] == "cached"
        assert result["notice"] == "Dated saved response (one-hour refresh limit)."
        assert result["observations"] == record()["observations"]


def test_stale_cache_offline_and_after_failure(cache_root, monkeypatch):
    """A stale cache is used offline or after a failed refresh, with distinct notices."""
    stale = record(fetched_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat())
    write_json(cache_root / f"{CODE}.json", stale)
    assert price_api.fetch_observations(CODE, offline=True)["notice"] == (
        "Dated saved response (one-hour refresh limit).")
    monkeypatch.setattr(price_api, "get_json", offline_network)
    result = price_api.fetch_observations(CODE)
    assert result["mode"] == "cached"
    assert result["notice"] == "Live request failed; showing dated saved observations."
    assert result["fetched_at"] == stale["fetched_at"]


def test_stale_cache_is_refreshed_when_online(cache_root, monkeypatch):
    """An expired cache does not block a live refresh."""
    write_json(cache_root / f"{CODE}.json",
               record(fetched_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat()))
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": []})
    assert price_api.fetch_observations(CODE)["mode"] == "live"


def test_offline_without_cache(cache_root, monkeypatch):
    """Offline mode never falls through to the network."""
    monkeypatch.setattr(price_api, "get_json", lambda *a: pytest.fail("network used"))
    with pytest.raises(ValueError, match="^No saved price response for this barcode.$"):
        price_api.fetch_observations(CODE, offline=True)


def test_invalid_cache_is_ignored(cache_root, monkeypatch):
    """A corrupt cache is neither served nor used as a failure fallback."""
    write_json(cache_root / f"{CODE}.json", record(complete_query="yes"))
    with pytest.raises(ValueError, match="^No saved price response"):
        price_api.fetch_observations(CODE, offline=True)
    monkeypatch.setattr(price_api, "get_json", offline_network)
    with pytest.raises(ValueError, match="^Price source unavailable; no saved response for this "
                                         "product.$"):
        price_api.fetch_observations(CODE)


@pytest.mark.parametrize("payload", [{}, {"items": None}, {"items": [{"product_code": CODE}]},
                                     {"items": [item(date="bad")]}])
def test_malformed_live_payloads_are_failures(payload, cache_root, monkeypatch):
    """Schema errors in the live payload are treated like an outage."""
    monkeypatch.setattr(price_api, "get_json", lambda *a: payload)
    with pytest.raises(ValueError, match="^Price source unavailable"):
        price_api.fetch_observations(CODE)
    assert not (cache_root / f"{CODE}.json").exists()
