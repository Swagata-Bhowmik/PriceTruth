"""Bounded, cached public price observations, never advertised as current retailer offers."""
import re
from datetime import UTC, date, datetime, timedelta

import requests

from price_truth.cache import fresh, read_json, write_json
from price_truth.calculations import positive
from price_truth.external import get_json
from price_truth.paths import EXTERNAL

URL = "https://prices.openfoodfacts.org/api/v1/prices"


def normalize(item: dict) -> dict:
    """Keep price evidence fields only; discard provider contributor/person fields."""
    product, store = item.get("product") or {}, item.get("location") or {}
    price = positive(item["price"])
    observed = date.fromisoformat(item["date"])
    if observed > latest_valid_date() or not re.fullmatch(r"[A-Z]{3}", str(item["currency"])):
        raise ValueError("Source returned an invalid date or currency.")
    return {"id": item["id"], "product_code": item.get("product_code"),
            "product_name": product.get("product_name") or item.get("product_name"),
            "price": price, "currency": item["currency"], "date": observed.isoformat(),
            "price_per": item.get("price_per"), "price_is_discounted": item.get("price_is_discounted"),
            "price_without_discount": item.get("price_without_discount"),
            "location_id": item.get("location_id"), "location_name": store.get("osm_name"),
            "location_type": store.get("osm_tag_key"), "proof_id": item.get("proof_id"),
            "duplicate_of": item.get("duplicate_of"),
            "source_url": f"https://prices.openfoodfacts.org/prices/{item['id']}"}


def latest_valid_date() -> date:
    """Contributors date prices in local time (India is UTC+5:30), so allow one day of clock skew."""
    return date.today() + timedelta(days=1)


def _normalize_valid(items: list[dict], code: str) -> tuple[list[dict], int]:
    """Normalize this barcode's rows, skipping individually malformed ones and counting them."""
    rows, skipped = [], 0
    for item in items:
        if str(item.get("product_code")) != code:
            continue
        try:
            rows.append(normalize(item))
        except (KeyError, TypeError, ValueError, OverflowError):
            skipped += 1
    return rows, skipped


def _saved_response(path, code: str) -> dict | None:
    """Return a schema-valid saved response for this barcode, or None."""
    cached = read_json(path)
    return cached if cached and valid_cache(cached, code) else None


def _live_observations(code: str) -> tuple[dict, list[dict]]:
    """Request one bounded page and keep valid normalized rows for this exact barcode only."""
    payload = get_json(URL, {"product_code": code, "size": 100, "order_by": "-date"})
    observations, skipped = _normalize_valid(payload["items"], code)
    if skipped and not observations:
        raise ValueError("Every observation in the response was malformed.")  # schema change: treat as outage
    return {**payload, "skipped_invalid": skipped}, observations


def fetch_observations(code: str, offline: bool = False) -> dict:
    """Fetch up to 100 observations; label truncation and retain a dated offline fallback."""
    if not re.fullmatch(r"[0-9]{8,14}", code):
        raise ValueError("Enter an 8-14 digit barcode.")
    path = EXTERNAL / "price_cache" / f"{code}.json"
    cached = _saved_response(path, code)
    if cached and (offline or fresh(cached)):
        return {**cached, "mode": "cached", "notice": "Dated saved response (one-hour refresh limit)."}
    if offline:
        raise ValueError("No saved price response for this barcode.")
    try:
        payload, observations = _live_observations(code)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        if cached:
            return {**cached, "mode": "cached", "notice": "Live request failed; showing dated saved observations."}
        raise ValueError("Price source unavailable; no saved response for this product.") from exc
    record = {"source": URL, "fetched_at": datetime.now(UTC).isoformat(), "license": "ODbL-1.0",
              "total_at_source": payload.get("total"), "complete_query": payload.get("pages", 1) <= 1,
              "skipped_invalid": payload["skipped_invalid"], "observations": observations}
    write_json(path, record)
    return {**record, "mode": "live", "notice": "Live retrieval of dated observations, not a live retailer quote."}


def valid_cache(record: dict, code: str) -> bool:
    """Reject schema-corrupt or wrong-product cache entries before they reach the UI."""
    try:
        timestamp = datetime.fromisoformat(record["fetched_at"])
        rows = record["observations"]
        if timestamp.tzinfo is None or not isinstance(rows, list) or not isinstance(record["complete_query"], bool):
            return False
        for row in rows:
            if str(row["product_code"]) != code:
                return False
            positive(row["price"])
            if date.fromisoformat(row["date"]) > latest_valid_date():
                return False
            if not re.fullmatch(r"[A-Z]{3}", row["currency"]):
                return False
        return True
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
