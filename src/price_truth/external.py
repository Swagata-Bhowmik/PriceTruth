"""Read-only Open Food Facts integration with explicit cached fallback."""
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import requests

from price_truth.cache import fresh, read_json, write_json
from price_truth.paths import EXTERNAL

HEADERS = {"User-Agent": "PriceTruthAcademic/0.1 (https://price-truth.netlify.app/)"}


def get_json(url: str, params: dict | None = None) -> dict:
    """Read a public API using a bounded request; never silently accept HTML."""
    response = requests.get(url, params=params, headers=HEADERS, timeout=(5, 15))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("The API returned an unexpected response.")
    return payload


def _cached_result(cached: dict | None, offline: bool, missing: str,
                   fresh_notice: dict, offline_notice: dict) -> dict | None:
    """Serve a fresh (online) or any saved (offline) response; None means fetch live."""
    if fresh(cached) and not offline:
        return {**cached, "mode": "cached", **fresh_notice}
    if not offline:
        return None
    if not cached:
        raise ValueError(missing)
    return {**cached, "mode": "cached", **offline_notice}


def lookup_product(code: str, offline: bool = False, cache_dir: Path | None = None) -> dict:
    """Fetch a numeric barcode, falling back only to a previously saved real response."""
    code = code.strip()
    if not re.fullmatch(r"[0-9]{8,14}", code):
        raise ValueError("Enter a barcode containing 8 to 14 digits.")
    cache_dir = cache_dir or EXTERNAL / "off"
    path = cache_dir / f"{code}.json"
    cached = read_json(path)
    saved = _cached_result(cached, offline,
                           "This barcode is not in the offline cache. Try a live lookup.",
                           {"notice": "Recently retrieved response (one-hour cache)."},
                           {"notice": "Offline saved response"})
    if saved:
        return saved
    url = f"https://world.openfoodfacts.org/api/v2/product/{code}.json"
    try:
        result = get_json(url, {"fields": "code,product_name,brands,quantity,product_quantity,"
                              "product_quantity_unit,categories,countries,last_modified_t"})
    except (requests.RequestException, ValueError) as exc:
        return _lookup_fallback(cached, exc)
    if result.get("status") != 1 or not result.get("product"):
        raise ValueError("No product found for this barcode.")
    record = {"product": result["product"], "source_url": url,
              "fetched_at": datetime.now(UTC).isoformat(), "license": "ODbL"}
    write_json(path, record)
    return {**record, "mode": "live", "notice": "Live Open Food Facts response"}


def _lookup_fallback(cached: dict | None, exc: Exception) -> dict:
    """Serve the saved record when the live source fails; otherwise report not-found or the outage."""
    response = getattr(exc, "response", None)
    # Open Food Facts answers 404 for barcodes it does not know: that is "not found", not an outage.
    if response is not None and response.status_code == 404 and not cached:
        raise ValueError("No product found for this barcode.") from exc
    if cached:
        return {**cached, "mode": "cached",
                "notice": f"Live lookup unavailable ({type(exc).__name__}); showing saved data."}
    raise ValueError("Live lookup is unavailable and no cached record exists.") from exc


def cached_products() -> list[dict]:
    """Expose saved names for offline browsing without inventing product information."""
    products = []
    for path in sorted((EXTERNAL / "off").glob("*.json")):
        record = read_json(path)
        if isinstance(record, dict) and isinstance(record.get("product"), dict) and record["product"].get("code"):
            products.append(record["product"])
    return products


SEARCH_URL = "https://search.openfoodfacts.org/search"


def _search_hits(query: str) -> list[dict]:
    """Request one page of full-text hits and reject a malformed hits field."""
    hits = get_json(SEARCH_URL, {"q": query, "page_size": 10})["hits"]
    if not isinstance(hits, list):
        raise ValueError("Unexpected search response.")
    return hits


def _search_summary(hit: dict) -> dict:
    """Keep only the display fields of a search hit."""
    return {"code": hit.get("code"), "product_name": hit.get("product_name_en") or hit.get("product_name"),
            "brands": hit.get("brands"), "quantity": hit.get("quantity")}


def search_products(query: str, offline: bool = False) -> dict:
    """Search the official full-text API, retaining a dated real-response fallback."""
    query = query.strip()
    if not 2 <= len(query) <= 100:
        raise ValueError("Use between 2 and 100 characters for a product search.")
    cache = EXTERNAL / "search" / (hashlib.sha256(query.lower().encode()).hexdigest() + ".json")
    cached = read_json(cache)
    saved = _cached_result(cached, offline,
                           "No saved results for this search. Try the barcode examples below.", {}, {})
    if saved:
        return saved
    try:
        hits = _search_hits(query)
    except (requests.RequestException, ValueError, KeyError) as exc:
        if cached:
            return {**cached, "mode": "cached"}
        raise ValueError("Live search is unavailable. Use a saved barcode example below.") from exc
    products = [_search_summary(h) for h in hits if re.fullmatch(r"\d{8,14}", str(h.get("code", "")))]
    result = {"query": query, "products": products, "source_url": SEARCH_URL,
              "fetched_at": datetime.now(UTC).isoformat(), "license": "ODbL"}
    write_json(cache, result)
    return {**result, "mode": "live"}
