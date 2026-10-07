"""Train and explain observed-price models; no synthetic authenticity labels."""
import json
import math
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from price_truth.calculations import discount_percent
from price_truth.data import load_catalogue
from price_truth.paths import MODEL, REPORTS

NUMERIC = ["log_listed_price", "rating", "log_rating_count"]
CATEGORICAL = ["platform", "category_group", "subcategory"]


def features(frame: pd.DataFrame) -> pd.DataFrame:
    """Use only known listing attributes; never selling price or derived discount."""
    out = frame[CATEGORICAL + ["listed_price", "rating", "rating_count"]].copy()
    out["log_listed_price"] = np.log1p(out.listed_price)
    out["log_rating_count"] = np.log1p(out.rating_count)
    return out[NUMERIC + CATEGORICAL]


def split_groups(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Split related normalized titles before any preprocessing or fitting."""
    indices = np.arange(len(frame))
    remaining, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42)
                           .split(indices, groups=frame.name_group))
    rest, calibration = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=43)
                            .split(remaining, groups=frame.iloc[remaining].name_group))
    rest, calibration = remaining[rest], remaining[calibration]
    train, validation = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=44)
                             .split(rest, groups=frame.iloc[rest].name_group))
    return {"train": rest[train], "validation": rest[validation],
            "calibration": calibration, "test": test}


def preprocessing() -> ColumnTransformer:
    """Fit missing-value treatment and category vocabulary on training data only."""
    return _preprocessing(NUMERIC)


def _preprocessing(numeric: list[str]) -> ColumnTransformer:
    """Build the shared transformer for an explicit list of numeric inputs."""
    return ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), numeric),
        ("category", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                                   max_categories=80, sparse_output=False), CATEGORICAL),
    ], verbose_feature_names_out=False)


def metrics(actual: np.ndarray, predicted_log: np.ndarray) -> dict:
    """Report currency errors and scale-balanced log error, not fraud accuracy."""
    predicted = np.maximum(np.expm1(predicted_log), 0)
    return {"n": len(actual), "mae_inr": float(mean_absolute_error(actual, predicted)),
            "median_absolute_percentage_error": float(np.median(np.abs(predicted - actual) / actual) * 100),
            "mean_absolute_log_error": float(mean_absolute_error(np.log1p(actual), predicted_log)),
            "r2": float(r2_score(actual, predicted))}


def observed_numeric(frame: pd.DataFrame) -> list[str]:
    """Numeric features with at least one observed value; a source may never record some.

    Flipkart listings carry no rating counts, so a Flipkart-only model must omit that
    feature explicitly instead of relying on the imputer to drop it with a warning.
    """
    data = features(frame)
    return [column for column in NUMERIC if data[column].notna().any()]


def baseline(train: pd.DataFrame, other: pd.DataFrame) -> np.ndarray:
    """Estimate selling price from training platform/category median price ratios."""
    ratios = train.assign(ratio=train.selling_price / train.listed_price)
    medians = ratios.groupby(["platform", "subcategory"]).ratio.median()
    fallback = float(ratios.ratio.median())
    return np.log1p([r.listed_price * medians.get((r.platform, r.subcategory), fallback)
                    for r in other.itertuples()])


def train_model() -> dict:
    """Select on validation data, calibrate separately, and evaluate a frozen test set."""
    started = time.perf_counter()
    frame = load_catalogue()
    splits = split_groups(frame)
    train, valid = frame.iloc[splits["train"]], frame.iloc[splits["validation"]]
    candidates = {
        "random_forest": RandomForestRegressor(n_estimators=100, max_depth=14,
                                                min_samples_leaf=8, n_jobs=2, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=180, max_leaf_nodes=20,
                                                               l2_regularization=2, random_state=42),
    }
    results = {"baseline": metrics(valid.selling_price.to_numpy(), baseline(train, valid))}
    for name, estimator in candidates.items():
        pipeline = make_pipeline(preprocessing(), estimator)
        pipeline.fit(features(train), np.log1p(train.selling_price))
        results[name] = metrics(valid.selling_price.to_numpy(), pipeline.predict(features(valid)))
    selected = min(candidates, key=lambda name: results[name]["mean_absolute_log_error"])
    fitting = frame.iloc[np.concatenate([splits["train"], splits["validation"]])]
    pipeline = make_pipeline(preprocessing(), candidates[selected])
    pipeline.fit(features(fitting), np.log1p(fitting.selling_price))
    calibration, test = frame.iloc[splits["calibration"]], frame.iloc[splits["test"]]
    residual = np.abs(np.log1p(calibration.selling_price) - pipeline.predict(features(calibration)))
    quantile = min(1., math.ceil((len(residual) + 1) * .9) / len(residual))
    radius = float(np.quantile(residual, quantile, method="higher"))
    predictions = pipeline.predict(features(test))
    actual_log = np.log1p(test.selling_price.to_numpy())
    test_results = metrics(test.selling_price.to_numpy(), predictions)
    test_results["interval_coverage"] = float(np.mean(np.abs(actual_log - predictions) <= radius))
    per_platform = {}
    for platform in ["amazon", "flipkart"]:
        mask = test.platform.to_numpy() == platform
        subset = fitting[fitting.platform == platform]
        separate = make_pipeline(_preprocessing(observed_numeric(subset)),
                                 candidates[selected].__class__(**candidates[selected].get_params()))
        separate.fit(features(subset), np.log1p(subset.selling_price))
        per_platform[platform] = {
            "combined_model": metrics(test.selling_price.to_numpy()[mask], predictions[mask]),
            "separate_model": metrics(test.selling_price.to_numpy()[mask], separate.predict(features(test[mask]))),
            "baseline": metrics(test.selling_price.to_numpy()[mask], baseline(fitting, test[mask])),
        }
    split_rows = frame[["key", "name_group", "platform"]].copy()
    split_rows["split"] = ""
    for name, positions in splits.items():
        split_rows.loc[positions, "split"] = name
    REPORTS.mkdir(parents=True, exist_ok=True)
    split_rows.to_csv(REPORTS / "evaluation_split.csv", index=False)
    by_group = fitting.groupby(["platform", "subcategory"]).size().to_dict()
    report = {
        "target": "log(1 + observed selling price in INR)", "selected_model": selected,
        "selection_criterion": "Lowest validation mean absolute log error among tree candidates",
        "validation": results, "test": test_results,
        "baseline_test": metrics(test.selling_price.to_numpy(), baseline(fitting, test)),
        "platform_comparison": per_platform,
        "splits": {k: len(v) for k, v in splits.items()},
        "unique_title_groups": int(frame.name_group.nunique()),
        "interval": {"nominal_coverage": .9, "log_radius": radius, "calibration_rows": len(residual)},
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": ["No ground-truth fraud labels; prediction is not authenticity verification.",
                        "Old/undated snapshots do not establish today's fair price.",
                        "Title normalization reduces but cannot eliminate variant leakage.",
                        "Listed price is a predictor, so inflated reference prices can bias estimates.",
                        "Calibration coverage assumes comparable data; it is not a per-product confidence score.",
                        "Platform and category shifts are confounded with unknown collection dates."]}
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "radius": radius, "support": by_group,
                 "training_keys": set(fitting.key), "report": report}, MODEL)
    (REPORTS / "model_evaluation.json").write_text(json.dumps(report, indent=2))
    return report


def load_model() -> dict:
    """Load only the trusted locally generated model; never accept uploaded pickle files."""
    return joblib.load(MODEL)


def assess(bundle: dict, listing: dict, selling_price: float, listed_price: float) -> dict:
    """Assess a quote against the historical catalogue model and compute real Tree SHAP."""
    import shap

    claimed = discount_percent(listed_price, selling_price)
    row = pd.DataFrame([{**listing, "listed_price": listed_price}])
    pipeline = bundle["pipeline"]
    transformed = pipeline.steps[0][1].transform(features(row))
    estimator = pipeline.steps[-1][1]
    estimate_log = float(estimator.predict(transformed)[0])
    estimate = float(np.expm1(estimate_log))
    lower = max(0., float(np.expm1(estimate_log - bundle["radius"])))
    upper = float(np.expm1(estimate_log + bundle["radius"]))
    support = bundle["support"].get((listing["platform"], listing["subcategory"]), 0)
    explanation = shap.TreeExplainer(estimator)(transformed)
    contributions = explanation.values[0]
    base = float(np.asarray(explanation.base_values).reshape(-1)[0])
    names = pipeline.steps[0][1].get_feature_names_out().tolist()
    status = "limited_support" if support < 30 else (
        "below_model_range" if selling_price < lower else
        "above_model_range" if selling_price > upper else "within_model_range")
    return {"claimed_discount_pct": claimed, "estimate": estimate, "lower": lower, "upper": upper,
            "status": status, "support": int(support), "prediction_log": estimate_log,
            "base_log": base, "shap": [{"feature": name, "contribution": float(value)}
                                         for name, value in zip(names, contributions, strict=True)],
            "explanation_error": abs(base + float(contributions.sum()) - estimate_log),
            "seen_in_training": listing.get("key") in bundle["training_keys"]}


if __name__ == "__main__":
    print(json.dumps(train_model(), indent=2))
