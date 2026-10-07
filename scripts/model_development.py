"""Evaluate improvements on development groups only; never retune against the old test."""
import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from price_truth.data import load_catalogue
from price_truth.model import CATEGORICAL, NUMERIC, features, metrics, preprocessing, split_groups
from price_truth.paths import MODEL, REPORTS


def estimator():
    """Keep the established tree settings fixed for the feature-ablation comparison."""
    return HistGradientBoostingRegressor(max_iter=180, max_leaf_nodes=20,
                                        l2_regularization=2, random_state=42)


def experiments() -> dict:
    """Compare a fixed baseline, text augmentation and an independent-price estimator."""
    text = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True)
    independent = ColumnTransformer([
        ("title", text, "name"),
        ("category", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    augmented = ColumnTransformer([
        ("established", preprocessing(), NUMERIC + CATEGORICAL),
        ("title", make_pipeline(text, TruncatedSVD(n_components=32, random_state=2026)), "name"),
    ])
    return {"established_features": make_pipeline(preprocessing(), estimator()),
            "title_augmented": make_pipeline(augmented, estimator()),
            "reference_price_free": make_pipeline(independent, Ridge(alpha=10, solver="lsqr"))}


def main() -> None:
    """Persist honest development evidence without replacing the deployed artifact."""
    frame = load_catalogue()
    original_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    splits = split_groups(frame)
    development = frame.iloc[splits["train"]]
    train_idx, validation_idx = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=2026)
                                     .split(development, groups=development.name_group))
    train, validation = development.iloc[train_idx], development.iloc[validation_idx]
    assert set(train.name_group).isdisjoint(validation.name_group)
    reserved = frame.iloc[np.concatenate([splits["test"], splits["calibration"], splits["validation"]])]
    assert set(development.name_group).isdisjoint(reserved.name_group)
    inputs = features(train).assign(name=train.name)
    checks = features(validation).assign(name=validation.name)
    changed = checks.copy()
    changed["log_listed_price"] = np.log1p(validation.listed_price.to_numpy()*1.25)
    results = {}
    errors = {}
    for name, pipeline in experiments().items():
        pipeline.fit(inputs, np.log1p(train.selling_price))
        prediction = pipeline.predict(checks)
        perturbed = pipeline.predict(changed)
        errors[name] = np.abs(np.log1p(validation.selling_price.to_numpy())-prediction)
        results[name] = {**metrics(validation.selling_price.to_numpy(), prediction),
                         "reference_plus_25pct_median_prediction_change_pct": float(np.median(
                             100*(np.expm1(perturbed)/np.maximum(np.expm1(prediction), .01)-1)))}
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == original_hash
    differences = pd.DataFrame({"group": validation.name_group.to_numpy(),
                                "difference": errors["title_augmented"]-errors["established_features"]})
    grouped = differences.groupby("group").difference.agg(["sum", "count"])
    rng = np.random.default_rng(2026)
    sampled = rng.integers(0, len(grouped), size=(1000, len(grouped)))
    changes = grouped["sum"].to_numpy()[sampled].sum(axis=1)/grouped["count"].to_numpy()[sampled].sum(axis=1)
    report = {"generated_at": datetime.now(UTC).isoformat(), "deployed_model_sha256": original_hash,
              "training_rows": len(train), "development_validation_rows": len(validation),
              "reserved_rows_not_used": len(reserved), "results": results,
              "lowest_development_log_error": min(results, key=lambda k: results[k]["mean_absolute_log_error"]),
              "title_minus_established_log_mae_group_bootstrap_95pct_interval": np.quantile(changes, [.025, .975]).tolist(),
              "deployment_decision": "Preserve existing model; candidate results are development evidence only.",
              "limitations": ["All records are historical; this does not establish present-day performance.",
                              "No new unseen market test set or fraud labels were introduced.",
                              "Do not compare these errors directly with the old test errors: different rows."]}
    out = REPORTS / "current"
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_development.json").write_text(json.dumps(report, indent=2))
    train[["key", "name_group"]].assign(experiment_split="train").to_csv(out / "development_train.csv", index=False)
    validation[["key", "name_group"]].assign(experiment_split="validation").to_csv(out / "development_validation.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
