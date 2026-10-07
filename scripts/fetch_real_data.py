"""Download a bounded INR Open Prices snapshot and cache genuine food records."""
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime

from price_truth.external import get_json, lookup_product
from price_truth.paths import EXTERNAL


def fetch_prices(params: dict, filename: str) -> list[dict]:
    """Save a bounded, attributed selection of observed prices."""
    url = "https://prices.openfoodfacts.org/api/v1/prices"
    first = get_json(url, params)
    items = list(first["items"])
    for page in range(2, min(first["pages"], 20) + 1):
        items.extend(get_json(url, {**params, "page": page})["items"])
    observations = []
    for item in items:
        product, location = item.get("product") or {}, item.get("location") or {}
        observations.append({
            "id": item["id"], "product_code": item.get("product_code"),
            "product_name": product.get("product_name") or item.get("product_name"),
            "price": item["price"], "currency": item["currency"], "date": item["date"],
            "price_per": item.get("price_per"), "price_is_discounted": item["price_is_discounted"],
            "price_without_discount": item.get("price_without_discount"),
            "location_id": item.get("location_id"), "location_name": location.get("osm_name"),
            "location_type": location.get("osm_tag_key"),
            "country": location.get("osm_address_country"), "proof_id": item.get("proof_id"),
            "duplicate_of": item.get("duplicate_of"),
            "source_url": f"https://prices.openfoodfacts.org/prices/{item['id']}",
        })
    record = {"source": url, "query": params, "fetched_at": datetime.now(UTC).isoformat(),
              "license": "ODbL-1.0", "total_at_source": first["total"],
              "complete_query": first["pages"] <= 20, "observations": observations}
    path = EXTERNAL / filename
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return observations


def main() -> None:
    """Keep the ODbL collection separate from the Kaggle catalogue."""
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    observations = fetch_prices({"currency": "INR", "size": 100,
                                 "date__lte": date.today().isoformat()}, "open_prices_inr.json")
    fetch_prices({"product_code": "3017620422003", "currency": "EUR", "location_id": 1920,
                  "size": 100, "date__lte": date.today().isoformat()}, "open_prices_example.json")
    codes = Counter(o["product_code"] for o in observations if o["product_code"])
    cached, failed = [], []
    for code, _ in codes.most_common(6):
        try:
            lookup_product(code)
            cached.append(code)
        except ValueError as exc:
            failed.append({"code": code, "error": str(exc)})
    summary = {"observations": len(observations), "unique_barcodes": len(codes),
               "cached_barcodes": cached, "lookup_failures": failed,
               "sha256": hashlib.sha256((EXTERNAL / "open_prices_inr.json").read_bytes()).hexdigest()}
    (EXTERNAL / "acquisition.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
