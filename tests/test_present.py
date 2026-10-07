"""Presentation helpers must translate results faithfully and never invent numbers."""
import json
import math

import pytest

from price_truth import present


def result(contributions, base=6.0):
    """A minimal assessment result with given log-space SHAP contributions."""
    estimate = math.expm1(base + sum(contributions.values()))
    return {"base_log": base, "estimate": estimate,
            "shap": [{"feature": k, "contribution": v} for k, v in contributions.items()]}


def test_effects_multiply_back_to_the_estimate():
    """Applying every percentage effect to the baseline reproduces the model estimate."""
    shap = {"log_listed_price": .4, "rating": -.05, "platform_amazon": .02, "platform_flipkart": -.01,
            "category_group_Clothing": .1, "subcategory_A > B > Shirts": -.2, "missingindicator_rating": .03}
    data = result(shap)
    effects = present.shap_effects(data, {"platform": "amazon", "category_group": "Clothing",
                                          "subcategory": "A > B > Shirts"}, top=99)
    product = math.prod(1 + e["effect_pct"] / 100 for e in effects["effects"])
    assert (1 + effects["baseline"]) * product - 1 == pytest.approx(data["estimate"])


def test_one_hot_columns_are_merged_under_the_listing_value():
    """Absent categories never appear as separate reasons."""
    shap = {"subcategory_X > Lingerie": .05, "subcategory_A > Cables": -.3, "rating": .01,
            "missingindicator_rating": .02}
    labels = [e["label"] for e in present.shap_effects(result(shap), {"subcategory": "A > Cables"})["effects"]]
    assert labels == ["Subcategory: Cables", "Customer rating"]
    assert not any("Lingerie" in label for label in labels)


def test_small_effects_are_grouped_as_other_factors():
    """Only the top factors are listed; the remainder is kept, not dropped."""
    shap = {f"subcategory_{i}": 0 for i in range(3)} | {"log_listed_price": .5, "rating": .1,
                                                       "log_rating_count": -.05}
    effects = present.shap_effects(result(shap), {}, top=1)["effects"]
    assert [e["label"] for e in effects] == ["Listed (MRP) price", "All other factors"]
    assert effects[1]["effect_pct"] == pytest.approx(100 * math.expm1(.05))


@pytest.mark.parametrize(("name", "label"), [
    ("log_listed_price", "Listed (MRP) price"), ("platform_flipkart", "Platform: Flipkart"),
    ("category_group_Personal care", "Category: Personal care"),
    ("subcategory_Clothing > Men's Clothing > Jeans", "Subcategory: Jeans"),
    ("subcategory_infrequent_sklearn", "Subcategory: rare subcategory"), ("odd_name", "odd name")])
def test_readable_feature_names(name, label):
    """Encoded column names become shopper-readable labels."""
    assert present.readable_feature(name) == label


def test_verdict_tables_cover_every_domain_status():
    """Each status the domain modules emit has a plain-language verdict."""
    assert set(present.ASSESSMENT) == {"below_model_range", "within_model_range", "above_model_range",
                                       "limited_support"}
    assert {"insufficient_history", "limited_history", "below_usual"} <= set(present.TIMING)
    assert {"evaluated", "baseline_preferred", "stale_history", "invalid_history"} <= set(present.FORECAST)
    assert present.verdict({}, "new_status") == ("New status", "", "neutral")


def test_money_formatting():
    """Rupees use the symbol; other currencies keep their code."""
    assert present.money(1234.4) == "₹1,234"
    assert present.money(12.345) == "₹12.35"
    assert present.money(3.5, "EUR") == "EUR 3.50"


def test_category_quality_flags_only_weak_groups(tmp_path):
    """Warnings come from the saved audit and only for R² below 0.5."""
    path = tmp_path / "audit.json"
    path.write_text(json.dumps({"subgroups": [
        {"platform": "flipkart", "category": "Electronics", "r2": -.57},
        {"platform": "amazon", "category": "Electronics", "r2": .92}]}))
    assert present.category_quality(path, "flipkart", "Electronics")["r2"] == -.57
    assert present.category_quality(path, "amazon", "Electronics") is None
    assert present.category_quality(tmp_path / "missing.json", "amazon", "Electronics") is None
