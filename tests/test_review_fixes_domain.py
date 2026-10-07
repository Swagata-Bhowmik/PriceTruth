"""Domain regression tests for the October 2026 review findings (included in the mutation run)."""
import json
from datetime import date, timedelta

import pandas as pd
import pytest
import requests

from price_truth import evidence_store, external, offers, price_api
from price_truth.observations import COLUMNS, validate_observations

CODE = "00001234"


def item(**changes):
    """One Open Prices API row for CODE."""
    return {"id": 1, "product_code": CODE, "price": 10, "currency": "INR", "date": date.today().isoformat(),
            **changes}


def test_latest_valid_date_allows_exactly_one_day_of_skew():
    """Finding 3: contributor dates up to tomorrow are accepted, later ones are not."""
    assert price_api.latest_valid_date() == date.today() + timedelta(days=1)


def test_normalize_valid_skips_and_counts_bad_rows_for_this_barcode_only():
    """Finding 3: other barcodes are ignored (not counted); each malformed row is counted once."""
    rows = [item(), item(id=2, price=None), item(id=3, currency=None), item(id=4, date="bad"),
            item(id=5, price="inf"), item(id=6, product_code="99999999", price=None), {"product_code": CODE}]
    kept, skipped = price_api._normalize_valid(rows, CODE)
    assert [r["id"] for r in kept] == [1] and skipped == 5
    assert price_api._normalize_valid([], CODE) == ([], 0)


def test_one_bad_row_does_not_discard_a_live_fetch(monkeypatch, tmp_path):
    """Finding 3: malformed rows are skipped and reported; tomorrow's date (UTC vs IST) is accepted."""
    monkeypatch.setattr(price_api, "EXTERNAL", tmp_path)
    rows = [item(), item(id=2, price=None), item(id=3, currency=None),
            item(id=4, date=(date.today() + timedelta(days=1)).isoformat()),
            item(id=5, date=(date.today() + timedelta(days=5)).isoformat())]
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": rows, "total": 5, "pages": 1})
    result = price_api.fetch_observations(CODE)
    assert [o["id"] for o in result["observations"]] == [1, 4]
    assert result["skipped_invalid"] == 3 and result["mode"] == "live" and result["complete_query"] is True
    saved = json.loads((tmp_path / "price_cache" / f"{CODE}.json").read_text())
    assert saved["skipped_invalid"] == 3 and len(saved["observations"]) == 2


def test_all_malformed_rows_count_as_an_outage(monkeypatch, tmp_path):
    """Finding 3: a page where every row is malformed is treated like a failed request."""
    monkeypatch.setattr(price_api, "EXTERNAL", tmp_path)
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": [item(price=None)], "total": 1})
    with pytest.raises(ValueError, match="^Price source unavailable") as failure:
        price_api.fetch_observations(CODE)
    assert str(failure.value.__cause__) == "Every observation in the response was malformed."
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": [], "total": 0})
    assert price_api.fetch_observations(CODE)["observations"] == []  # no data is not an error
    payload, rows = price_api._live_observations(CODE)
    assert payload["skipped_invalid"] == 0 and rows == []


def quotes(rows):
    """Validated test-only observations."""
    return validate_observations(pd.DataFrame([dict(zip(COLUMNS, r, strict=True)) for r in rows]))


def quote(store, day, price, quantity, unit):
    """One test-only quote for the same product and variant."""
    return ["p1", "Atta", "plain", store, "INR", day.isoformat(), price, quantity, unit, f"https://e.com/{store}"]


def test_old_quotes_of_another_size_do_not_block_ranking():
    """Finding 5: only the quotes being ranked must share a pack size."""
    today = date.today()
    data = quotes([quote("A", today - timedelta(days=30), 30, 500, "g"), quote("A", today, 55, 1, "kg"),
                   quote("B", today, 52, 1000, "g")])
    ranked = offers.compare_observed_offers(data, True, today)
    assert ranked.store.tolist() == ["B", "A"] and ranked.age_days.tolist() == [0, 0]


def test_recent_quotes_of_different_sizes_are_still_rejected():
    """Finding 5: the pack check still applies to the quotes that are ranked."""
    today = date.today()
    with pytest.raises(ValueError, match="same total pack quantity"):
        offers.compare_observed_offers(quotes([quote("A", today, 55, 1, "kg"), quote("B", today, 30, 500, "g")]),
                                       True, today)
    with pytest.raises(ValueError, match="same total pack quantity"):
        offers.compare_observed_offers(quotes([quote("A", today, 55, 1, "kg"), quote("B", today, 30, 1, "l")]),
                                       True, today)
    with pytest.raises(ValueError, match="^Need at least two stores with quotes dated today or yesterday.$"):
        offers.compare_observed_offers(quotes([quote("A", today - timedelta(days=9), 55, 1, "kg"),
                                               quote("B", today - timedelta(days=9), 52, 1, "kg")]), True, today)


def test_require_same_pack_compares_normalised_quantities():
    """1 kg equals 1000 g; 1 kg is not 999 g; mass is not volume."""
    frame = lambda units: pd.DataFrame({"quantity": [q for q, _ in units], "unit": [u for _, u in units]})  # noqa: E731
    offers.require_same_pack(frame([(1, "kg"), (1000, "g")]))
    for bad in [[(1, "kg"), (999, "g")], [(1, "kg"), (1, "l")], [(2, "count"), (1, "count")]]:
        with pytest.raises(ValueError):
            offers.require_same_pack(frame(bad))


@pytest.mark.parametrize("record", [
    {"source": "s", "license": "l", "observations": []},
    {"source": "s", "license": "l", "fetched_at": "2026-01-01T00:00:00", "observations": []},
    {"source": "s", "license": "l", "fetched_at": "yesterday", "observations": []},
    {"source": "s", "license": "l", "fetched_at": None, "observations": []},
])
def test_malformed_archive_snapshot_is_a_handled_error(tmp_path, record):
    """Finding 6: missing, unparseable or timezone-less retrieval times raise the error the page handles."""
    (tmp_path / "a.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="Archived snapshot"):
        evidence_store.accumulated_observations(tmp_path)


def test_valid_archive_still_loads(tmp_path):
    """A well-formed aware snapshot is accepted."""
    record = {"source": "s", "license": "l", "fetched_at": "2026-01-01T00:00:00+00:00",
              "observations": [{"id": 1, "price": 2}]}
    (tmp_path / "a.json").write_text(json.dumps(record))
    frame, meta = evidence_store.accumulated_observations(tmp_path)
    assert len(frame) == 1 and meta["snapshots"] == 1


def test_corrupt_saved_products_are_skipped(monkeypatch, tmp_path):
    """Finding 7: a corrupt or incomplete saved file does not break the product list."""
    (tmp_path / "off").mkdir()
    (tmp_path / "off" / "1.json").write_text("{broken")
    (tmp_path / "off" / "2.json").write_text(json.dumps({"no_product": True}))
    (tmp_path / "off" / "3.json").write_text(json.dumps({"product": {"product_name": "No code"}}))
    (tmp_path / "off" / "4.json").write_text(json.dumps({"product": "text"}))
    (tmp_path / "off" / "5.json").write_text(json.dumps({"product": {"code": "123", "product_name": "Ok"}}))
    monkeypatch.setattr(external, "EXTERNAL", tmp_path)
    assert [p["code"] for p in external.cached_products()] == ["123"]


def test_unknown_barcode_with_saved_copy_serves_the_copy(monkeypatch, tmp_path):
    """A 404 for a barcode we have saved still serves the saved record, labelled as such."""
    response = requests.Response()
    response.status_code = 404
    (tmp_path / "12345678.json").write_text(json.dumps({"product": {"code": "12345678"}, "source_url": "u",
                                                        "fetched_at": "2025-01-01T00:00:00+00:00",
                                                        "license": "ODbL"}))

    def not_found(*args, **kwargs):
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(external, "get_json", not_found)
    result = external.lookup_product("12345678", False, tmp_path)
    assert result["mode"] == "cached" and "unavailable" in result["notice"]


def test_saved_responses_accept_tomorrow_dated_rows():
    """A cached row dated tomorrow (contributor timezone) stays valid; two days ahead does not."""
    from datetime import UTC, datetime

    good = price_api.normalize(item(date=(date.today() + timedelta(days=1)).isoformat()))
    record = {"fetched_at": datetime.now(UTC).isoformat(), "complete_query": True, "observations": [good]}
    assert price_api.valid_cache(record, CODE) is True
    record["observations"] = [{**good, "date": (date.today() + timedelta(days=2)).isoformat()}]
    assert price_api.valid_cache(record, CODE) is False
