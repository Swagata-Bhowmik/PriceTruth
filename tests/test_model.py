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
