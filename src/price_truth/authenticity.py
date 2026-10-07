"""Discount-authenticity classifier trained on synthetic labelled offers.

Labels come from the 30-day lowest-price reference rule applied to simulated histories
(see synthetic.reference_check). Inputs are only what a shopper sees on a listing.
"""
import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from price_truth.paths import DATA, REPORTS, ROOT

MODEL = ROOT / "artifacts" / "discount_model.joblib"
TRAINING = DATA / "final" / "discount_training.csv.gz"
NUMERIC = ["log_listed_price", "price_ratio", "claimed_discount_pct", "rating", "log_rating_count"]
CATEGORICAL = ["platform", "category_group", "in_sale_event"]


def features(frame: pd.DataFrame) -> pd.DataFrame:
    """Shopper-visible inputs only; the 30-day history is not available at inference."""
    out = pd.DataFrame({"platform": frame.platform, "category_group": frame.category_group,
                        "in_sale_event": frame.in_sale_event.astype(str)})
    out["log_listed_price"] = np.log1p(frame.listed_price.astype(float))
    out["price_ratio"] = frame.selling_price.astype(float) / frame.listed_price.astype(float)
    out["claimed_discount_pct"] = 100 * (1 - out.price_ratio)
    out["rating"] = pd.to_numeric(frame.rating, errors="coerce")
    out["log_rating_count"] = np.log1p(pd.to_numeric(frame.rating_count, errors="coerce"))
    return out[NUMERIC + CATEGORICAL]


def preprocessing() -> ColumnTransformer:
    """Median-impute numbers with missing flags; one-hot encode categories."""
    return ColumnTransformer([
        ("num", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)],
        verbose_feature_names_out=False)


def scores(actual: np.ndarray, probability: np.ndarray, threshold: float = .5) -> dict:
    """Ranking, threshold and calibration metrics."""
    predicted = probability >= threshold
    return {"n": int(len(actual)), "positive_rate": float(actual.mean()),
            "roc_auc": float(roc_auc_score(actual, probability)),
            "average_precision": float(average_precision_score(actual, probability)),
            "precision": float(precision_score(actual, predicted, zero_division=0)),
            "recall": float(recall_score(actual, predicted, zero_division=0)),
            "f1": float(f1_score(actual, predicted, zero_division=0)),
            "brier": float(brier_score_loss(actual, probability))}


def label_rule() -> str:
    """The labelling rule with its configured numbers."""
    from price_truth.synthetic import assumptions

    rules = assumptions()["labels"]
    return (f"Inflated when the advertised discount is at least {rules['threshold_pp']} points above the product's "
            f"90-day median discount while the price is less than {rules['min_real_saving_pct']}% below its lowest "
            "price in the 30 days before the promotion.")


def best_threshold(actual: np.ndarray, probability: np.ndarray) -> float:
    """Probability cut-off with the highest F1 on validation data."""
    candidates = np.unique(np.round(probability, 3))
    return float(max(candidates, key=lambda t: f1_score(actual, probability >= t, zero_division=0)))


def train(frame: pd.DataFrame | None = None) -> dict:
    """Group-split by product so no product appears in both training and test data."""
    frame = frame if frame is not None else pd.read_csv(TRAINING)
    target = frame.inflated.astype(bool).to_numpy()
    outer = GroupShuffleSplit(n_splits=1, test_size=.2, random_state=11)
    fit_idx, test_idx = next(outer.split(frame, target, frame.key))
    fitting, test = frame.iloc[fit_idx], frame.iloc[test_idx]
    candidates = {"logistic_regression": LogisticRegression(max_iter=2000),
                  "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=11, max_iter=300,
                                                                           learning_rate=.08)}
    inner = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=12)
    train_idx, val_idx = next(inner.split(fitting, fitting.inflated, fitting.key))
    validation, thresholds = {}, {}
    for name, estimator in candidates.items():
        pipeline = make_pipeline(preprocessing(), estimator)
        pipeline.fit(features(fitting.iloc[train_idx]), fitting.inflated.iloc[train_idx].astype(bool))
        probability = pipeline.predict_proba(features(fitting.iloc[val_idx]))[:, 1]
        actual = fitting.inflated.iloc[val_idx].astype(bool).to_numpy()
        thresholds[name] = best_threshold(actual, probability)
        validation[name] = scores(actual, probability, thresholds[name])
    selected = max(validation, key=lambda n: validation[n]["average_precision"])
    threshold = thresholds[selected]
    pipeline = make_pipeline(preprocessing(), candidates[selected])
    pipeline.fit(features(fitting), fitting.inflated.astype(bool))
    probability = pipeline.predict_proba(features(test))[:, 1]
    by_category = {}
    for category, rows in test.assign(p=probability).groupby("category_group"):
        if rows.inflated.nunique() == 2 and len(rows) >= 50:
            by_category[category] = scores(rows.inflated.astype(bool).to_numpy(), rows.p.to_numpy(), threshold)
    report = {"generated_at": datetime.now(UTC).isoformat(), "selected_model": selected,
              "selection_criterion": "Highest validation average precision",
              "label_rule": label_rule(),
              "data": "Synthetic labelled offers (provenance='synthetic'); products are group-split.",
              "rows": {"fit": int(len(fitting)), "test": int(len(test)),
                       "products": int(frame.key.nunique())},
              "threshold": threshold, "threshold_rule": "Maximises F1 on the validation products",
              "validation": validation,
              "test": scores(test.inflated.astype(bool).to_numpy(), probability, threshold),
              "test_by_category": by_category}
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "threshold": threshold, "report": report}, MODEL)
    (REPORTS / "discount_model_evaluation.json").write_text(json.dumps(report, indent=2))
    return report


def load() -> dict:
    """Load the trusted locally trained classifier."""
    return joblib.load(MODEL)


def assess_discount(bundle: dict, listing: dict, selling_price: float, listed_price: float,
                    in_sale_event: bool) -> dict:
    """Probability that an advertised discount is inflated, with Tree SHAP or linear contributions."""
    row = pd.DataFrame([{**listing, "listed_price": listed_price, "selling_price": selling_price,
                         "in_sale_event": in_sale_event}])
    pipeline = bundle["pipeline"]
    transformer, estimator = pipeline.steps[0][1], pipeline.steps[-1][1]
    transformed = transformer.transform(features(row))
    probability = float(estimator.predict_proba(transformed)[0, 1])
    names = transformer.get_feature_names_out().tolist()
    if isinstance(estimator, HistGradientBoostingClassifier):
        import shap

        values = shap.TreeExplainer(estimator)(transformed).values[0]
    else:
        values = transformed[0] * estimator.coef_[0]  # log-odds contributions of a linear model
    return {"probability_inflated": probability, "flagged": probability >= bundle.get("threshold", .5),
            "threshold": bundle.get("threshold", .5),
            "contributions": [{"feature": n, "contribution": float(v)}
                              for n, v in zip(names, np.ravel(values), strict=True)]}
