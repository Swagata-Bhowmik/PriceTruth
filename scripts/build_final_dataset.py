"""Build the finalized Price Truth dataset: real listings plus seeded synthetic layers.

Writes datasets/final/* and trains the discount-authenticity classifier. Re-running on the
same day reproduces identical files; later runs only append newer days to each history.
"""
import json
from datetime import UTC, date, datetime

import pandas as pd

from price_truth import authenticity, synthetic
from price_truth.data import load_catalogue
from price_truth.external import lookup_product
from price_truth.paths import DATA, EXTERNAL

FINAL = DATA / "final"
HISTORY_PRODUCTS_PER_GROUP = 40
LABEL_PRODUCTS_PER_GROUP = 160
LABEL_SAMPLES = 10
FOOD_PRODUCTS, FOOD_STORES = 30, 2


def stratified(catalogue: pd.DataFrame, per_group: int, salt: str) -> pd.DataFrame:
    """Same-size sample from every platform × category group (all rows when a group is small)."""
    seed = synthetic.seed_for(salt) % 2**32
    parts = [g.sample(min(len(g), per_group), random_state=seed)
             for _, g in catalogue.groupby(["platform", "category_group"])]
    return pd.concat(parts, ignore_index=True)


def food_prices(end: date) -> pd.DataFrame:
    """Real Open Prices INR observations plus anchored synthetic daily store histories."""
    snapshot = json.loads((EXTERNAL / "current/open_prices_inr.json").read_bytes())
    real = pd.DataFrame(snapshot["observations"]).assign(provenance="real")
    named = real[real.product_name.notna() & (real.location_type == "shop")]
    anchors = (named.groupby(["product_code", "product_name"]).price.median().reset_index()
               .sort_values("product_code").head(FOOD_PRODUCTS))
    for code in anchors.product_code:  # cache real Open Food Facts pack details; skip if offline
        try:
            lookup_product(code)
        except ValueError:
            pass
    simulated = [synthetic.food_history(row.product_code, row.product_name, float(row.price), 900001 + store, end)
                 for row in anchors.itertuples() for store in range(FOOD_STORES)]
    simulated = pd.concat(simulated, ignore_index=True).dropna(axis=1, how="all")
    return pd.concat([real, simulated], ignore_index=True)


def shrink_cases() -> dict:
    """Merge cited real cases with simulated generic timelines (provenance on every case)."""
    real = json.loads((DATA / "evidence/shrink_cases.json").read_bytes())
    extra = json.loads((FINAL / "shrink_research.json").read_bytes()) if (FINAL / "shrink_research.json").exists() \
        else {"cases": []}
    simulated = json.loads((FINAL / "shrink_simulated.json").read_bytes())["cases"]
    cases = [{**c, "provenance": "real", "source_name": real["source_name"], "source_url": real["source_url"],
              "reported_on": real["reported_on"]} for c in real["cases"]]
    cases += [{**c, "provenance": "real"} for c in extra["cases"]]
    cases += [{**c, "provenance": "synthetic"} for c in simulated]
    return {"generated_at": datetime.now(UTC).isoformat(), "cases": cases}


def main() -> None:
    """Generate every synthetic layer, write the data card inputs and train the classifier."""
    end = min(date.today(), synthetic.HORIZON)
    catalogue = load_catalogue()
    FINAL.mkdir(parents=True, exist_ok=True)
    history_sample = stratified(catalogue, HISTORY_PRODUCTS_PER_GROUP, "history-sample")
    histories = pd.concat([synthetic.price_history(r, end) for r in history_sample.to_dict("records")])
    histories.assign(date=histories.date.dt.date.astype(str)).to_csv(FINAL / "price_history.csv.gz", index=False)
    label_sample = stratified(catalogue, LABEL_PRODUCTS_PER_GROUP, "label-sample")
    labels = pd.concat([synthetic.labelled_examples(r, LABEL_SAMPLES, end) for r in label_sample.to_dict("records")])
    labels.to_csv(FINAL / "discount_training.csv.gz", index=False)
    offers = pd.concat([synthetic.offers_for(r, end).assign(key=r["key"]) for r in history_sample.to_dict("records")])
    offers.to_csv(FINAL / "offers.csv", index=False)
    food = food_prices(end)
    food.to_csv(FINAL / "food_prices.csv.gz", index=False)
    cases = shrink_cases()
    (FINAL / "shrink_cases.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
    report = authenticity.train(labels)
    summary = {"generated_at": datetime.now(UTC).isoformat(), "end_date": end.isoformat(),
               "real_listings": int(len(catalogue)),
               "price_history": {"products": int(history_sample.key.nunique()), "rows": int(len(histories)),
                                 "first_date": synthetic.START.isoformat(), "last_date": end.isoformat()},
               "discount_training": {"products": int(label_sample.key.nunique()), "rows": int(len(labels)),
                                     "inflated_share": float(labels.inflated.mean())},
               "offers": {"products": int(offers.key.nunique()), "rows": int(len(offers))},
               "food_prices": food.provenance.value_counts().to_dict(),
               "shrink_cases": pd.Series([c["provenance"] for c in cases["cases"]]).value_counts().to_dict(),
               "discount_model_test": report["test"]}
    (FINAL / "build_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
