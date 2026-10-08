"""Verify explanations against the real trained artifact and held-out listings."""
import numpy as np
import pandas as pd
import pytest

from price_truth.data import load_catalogue
from price_truth.model import assess, features, load_model
from price_truth.paths import REPORTS


@pytest.fixture(scope="module")
def bundle():
    """Load the trained artifact once."""
    return load_model()


@pytest.mark.parametrize("platform", ["amazon", "flipkart"])
def test_shap_reconstructs_actual_prediction(bundle, platform):
    """Every explanation must add up in the model's stated output space."""
    splits = pd.read_csv(REPORTS / "evaluation_split.csv")
    keys = splits[(splits.platform == platform) & (splits.split == "test")].key
    row = load_catalogue().set_index("key", drop=False).loc[keys.iloc[0]].to_dict()
    result = assess(bundle, row, row["selling_price"], row["listed_price"])
    assert result["explanation_error"] < 1e-6
    assert result["lower"] <= result["estimate"] <= result["upper"]
    assert not result["seen_in_training"]
    assert np.isfinite(result["estimate"]) and result["estimate"] > 0


def test_missing_rating_does_not_break_inference(bundle):
    """Flipkart records can be scored without inventing ratings or counts."""
    data = load_catalogue()
    rows = data[(data.platform == "flipkart") & data.rating.isna()].head(5)
    assert np.isfinite(bundle["pipeline"].predict(features(rows))).all()


def test_invalid_quote_and_sparse_category(bundle):
    """Inverted prices fail validation and unsupported categories abstain."""
    row = load_catalogue().iloc[0].to_dict()
    with pytest.raises(ValueError):
        assess(bundle, row, 200, 100)
    row["subcategory"] = "Unseen category"
    assert assess(bundle, row, 100, 200)["status"] == "limited_support"


@pytest.mark.filterwarnings("error::UserWarning")
def test_training_pipeline_on_real_data(monkeypatch, tmp_path):
    """Exercise fitting, calibration, and artifact output in an isolated directory."""
    from price_truth import model
    monkeypatch.setattr(model, "MODEL", tmp_path / "model.joblib")
    monkeypatch.setattr(model, "REPORTS", tmp_path)
    result = model.train_model()
    assert (tmp_path / "model.joblib").exists()
    assert sum(result["splits"].values()) == len(load_catalogue())
    assert result["interval"]["calibration_rows"] == result["splits"]["calibration"]
    assert result["test"]["mean_absolute_log_error"] < result["baseline_test"]["mean_absolute_log_error"]


def test_sparse_subcategory_falls_back_to_category_group(bundle):
    """A thin subcategory is compared at platform + category level when that has enough training listings."""
    from price_truth.model import comparison_basis, with_group_support

    data = load_catalogue()
    enriched = with_group_support(dict(bundle), data)
    assert with_group_support(enriched, data.head(0)) is enriched  # stored counts are never recomputed
    row = data.iloc[0].to_dict()
    row["subcategory"] = "Unseen category"
    assert comparison_basis(enriched, row)[0] == "category"
    result = assess(enriched, row, 100, 200)
    assert result["comparison_basis"] == "category" and result["status"] != "limited_support"
    assert result["support"] == 0 and result["group_support"] >= 30
    row["category_group"] = "Unseen group"
    assert assess(enriched, row, 100, 200)["status"] == "limited_support"
    exact = data.iloc[0].to_dict()
    exact_basis, support, _ = comparison_basis(enriched, exact)
    assert (exact_basis == "subcategory") == (support >= 30)
