"""Audit the frozen historical model on held-out rows; do not tune on these diagnostics."""
import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from price_truth.data import load_catalogue
from price_truth.model import features, load_model, metrics
from price_truth.paths import MODEL, REPORTS


def main() -> None:
    """Record subgroup errors and sensitivity to reference prices with held-out provenance."""
    data, bundle = load_catalogue(), load_model()
    splits = pd.read_csv(REPORTS / "evaluation_split.csv")
    keys = splits.loc[splits.split == "test", "key"]
    test = data[data.key.isin(keys)].copy()
    assert len(test) == len(keys) and not set(test.key) & bundle["training_keys"]
    prediction = bundle["pipeline"].predict(features(test))
    test["predicted_log"] = prediction
    groups = []
    for (platform, category), group in test.groupby(["platform", "category_group"]):
        if len(group) >= 30:
            groups.append({"platform": platform, "category": category,
                           **metrics(group.selling_price.to_numpy(), group.predicted_log.to_numpy())})
    perturbed = test.assign(listed_price=test.listed_price * 1.25)
    shifted = bundle["pipeline"].predict(features(perturbed))
    influence = 100 * (np.expm1(shifted) / np.expm1(prediction) - 1)
    record = {"generated_at": datetime.now(UTC).isoformat(),
              "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
              "held_out_rows": len(test), "overall": metrics(test.selling_price.to_numpy(), prediction),
              "subgroups_minimum_n": 30, "subgroups": groups,
              "reference_price_sensitivity": {"perturbation_pct": 25,
                  "median_prediction_change_pct": float(np.median(influence)),
                  "p90_prediction_change_pct": float(np.quantile(influence, .9)),
                  "scope": "Controlled feature perturbation, not new market observations or a causal estimate"},
              "limitations": ["Historical snapshots cannot establish prospective performance.",
                              "Diagnostic subgroup results must not be used to retune against the frozen test set."]}
    folder = REPORTS / "current"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model_audit.json").write_text(json.dumps(record, indent=2))
    print(json.dumps({"held_out_rows": len(test), "sensitivity": record["reference_price_sensitivity"]}, indent=2))


if __name__ == "__main__":
    main()
