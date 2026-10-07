"""Audit current public INR observations without replacing the submitted source snapshot."""
import json
from datetime import UTC, date, datetime

import pandas as pd

from price_truth.cache import write_json
from price_truth.evidence_store import accumulated_observations, archive_snapshot, history_readiness
from price_truth.external import get_json
from price_truth.paths import EXTERNAL, REPORTS
from price_truth.price_api import URL, normalize


def main() -> None:
    """Read at most ten API pages; record provenance, completeness and history coverage."""
    params = {"currency": "INR", "size": 100, "date__lte": date.today().isoformat()}
    first = get_json(URL, params)
    items = first["items"]
    for page in range(2, min(first["pages"], 10)+1):
        items.extend(get_json(URL, {**params, "page": page})["items"])
    observations = [normalize(i) for i in items]
    record = {"source": URL, "query": params, "fetched_at": datetime.now(UTC).isoformat(),
              "license": "ODbL-1.0", "complete_query": first["pages"] <= 10,
              "total_at_source": first["total"], "observations": observations}
    out = EXTERNAL / "current"
    out.mkdir(parents=True, exist_ok=True)
    archive_snapshot(record, EXTERNAL / "archive")
    write_json(out / "open_prices_inr.json", record)
    frame = pd.DataFrame(observations)
    eligible = frame[(frame.location_type == "shop") & frame.proof_id.notna()
                     & frame.duplicate_of.isna() & frame.product_code.notna()]
    groups = eligible.groupby(["product_code", "location_id", "currency", "price_per"], dropna=False)
    counts = groups.date.nunique().sort_values(ascending=False)
    summary = {"fetched_at": record["fetched_at"], "raw_observations": len(frame),
               "identified_barcodes": int(frame.product_code.nunique()),
               "eligible_shop_observations": len(eligible), "complete_query": record["complete_query"],
               "largest_distinct_date_count": int(counts.max()) if len(counts) else 0,
               "groups_with_at_least_40_dates": int((counts >= 40).sum()),
               "top_histories": [{"barcode": key[0], "store": key[1], "currency": key[2],
                                  "basis": str(key[3]), "dates": int(n)} for key, n in counts.head(10).items()],
               "conclusion": "Counts describe observed data only; they do not establish pack continuity or forecast accuracy."}
    folder = REPORTS / "current"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "data_feasibility.json").write_text(json.dumps(summary, indent=2))
    accumulated, metadata = accumulated_observations(EXTERNAL / "archive")
    history_readiness(accumulated).to_csv(folder / "history_readiness.csv", index=False)
    write_json(folder / "collection_status.json", metadata)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
