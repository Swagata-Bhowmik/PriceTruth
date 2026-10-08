"""Source integrity, normalization, and evaluation leakage checks."""
import hashlib
import json

import pandas as pd
import pytest

from price_truth.data import (
    SOURCES,
    amazon_variant,
    category_parts,
    clean_source,
    flipkart_variant,
    load_catalogue,
    normalize,
    numeric,
    title_category,
)
from price_truth.model import features
from price_truth.paths import REPORTS


def test_raw_hashes_and_partition():
    """Every source row is accounted for and both original files stay unchanged."""
    audit = json.loads((REPORTS / "data_audit.json").read_text())
    expected = {"amazon": "4ba126c4ba8edd35e62e94ce1c853073d832de380184ab4f5f97d1e314882c77",
                "flipkart": "56f8f699c9e847356666c2eab3c3ab1244340f6a98ad08e39ea2199ebe993ad1"}
    for name, (path, _, _) in SOURCES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[name]
        source = audit["sources"][name]
        assert source["raw_rows"] == source["clean_rows"] + sum(source["exclusions"].values())


def test_catalogue_invariants():
    """Rows have valid prices and unique platform-specific identities."""
    data = load_catalogue()
    assert data.key.is_unique
    assert (data.selling_price > 0).all()
    assert (data.listed_price >= data.selling_price).all()
    amazon, flipkart = data[data.platform == "amazon"], data[data.platform == "flipkart"]
    assert amazon.observed_at.str.startswith("2023-01-05").all()  # recovered from qid timestamps
    assert amazon.brand.ne("").all() and amazon.brand_source.eq("title_first_word").all()
    unrated = flipkart.rating.isna()
    assert flipkart[unrated].rating_count.isin([0, None]).all()
    assert flipkart[~unrated].rating_count.isna().all()
    assert data.provenance.eq("real").all()


def test_conflicting_actual_source_prices_are_quarantined():
    """Repeated IDs with changed selling OR reference prices are ambiguous."""
    raw = pd.read_csv(SOURCES["amazon"][0], dtype=str, keep_default_na=False)
    raw = raw[raw.product_id.isin(["B096MSW6CT", "B0B5B6PQCT", "B07JW9H4J1"])].reset_index(drop=True)
    clean, excluded, _ = clean_source(normalize("amazon", raw))
    assert clean.product_id.tolist() == ["B07JW9H4J1"]
    assert len(clean) + len(excluded) == len(raw)


def test_numeric_missing_is_not_zero():
    """Missing or malformed ratings must remain missing."""
    parsed = numeric(pd.Series(["₹1,099", "4.2", "No rating available", "", "|", "inf"]))
    assert parsed.iloc[:2].tolist() == [1099, 4.2]
    assert parsed.iloc[2:].isna().all()


@pytest.mark.parametrize("value", ["not json", "[]", "{}", "null"])
def test_category_rejects_invalid_structure(value):
    """Malformed source fields must not be executed or crash normalization."""
    assert category_parts(value, "flipkart") == []


def test_no_target_leakage_in_features():
    """Changing the prediction target must not change the model inputs."""
    data = load_catalogue().head(4)
    original = features(data)
    data["selling_price"] *= 10
    data["discount_pct"] = 100
    pd.testing.assert_frame_equal(features(data), original)


def test_build_catalogue_reproduces_shipped_catalogue(monkeypatch, tmp_path):
    """Rebuilding from the original sources in isolation reproduces the shipped catalogue."""
    from price_truth import data
    monkeypatch.setattr(data, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(data, "REPORTS", tmp_path / "reports")
    report = data.build_catalogue()
    shipped = json.loads((REPORTS / "data_audit.json").read_text())
    assert report["combined_rows"] == shipped["combined_rows"] == len(load_catalogue())
    assert (report["synthetic_observations"], report["authenticity_labels"]) == (0, 0)
    fields = ["sha256", "clean_rows", "exclusions"]
    assert {name: [report["sources"][name][f] for f in fields] for name in SOURCES} == {
        name: [shipped["sources"][name][f] for f in fields] for name in SOURCES}
    rebuilt = pd.read_csv(tmp_path / "processed" / "catalogue.csv", dtype={"product_id": str})
    assert rebuilt.key.tolist() == load_catalogue().key.tolist()
    assert json.loads((tmp_path / "reports" / "data_audit.json").read_text()) == report
    excluded = pd.read_csv(tmp_path / "processed" / "excluded.csv")
    assert len(excluded) == sum(sum(s["exclusions"].values()) for s in report["sources"].values())


def test_evaluation_groups_do_not_overlap():
    """Related normalized titles must appear in exactly one split."""
    splits = pd.read_csv(REPORTS / "evaluation_split.csv")
    assert splits.groupby("name_group").split.nunique().max() == 1
    assert splits.key.is_unique
    assert set(splits.split) == {"train", "validation", "calibration", "test"}



@pytest.mark.parametrize(("title", "group"), [
    ("Clovia Women's Full Coverage Bra", "Clothing"), ("Treppe Bellies", "Footwear"),
    ("Pout Brass Bangle", "Jewellery"), ("Olvin Oval Sunglasses", "Fashion accessories"),
    ("Speedwav 186136 Manual Rear View Mirror", "Automotive"),
    ("Corcepts Universal Tablet HD Ultra Clear Transparency Guard Glass", "Electronics"),
    ("Ocean GP/Pyramid Glass (300 ml, Clear, Pack of 12)", "Home and kitchen"),
    ("Sumo Baby Walker (Red)", "Baby and kids"), ("Zixtro Bug", "Other"),
])
def test_title_category_rules(title, group):
    """Whole-word title rules classify rows whose category field holds the product name."""
    assert title_category(title) == group


def test_category_groups_cover_source_roots():
    """Almost every listing gets a real category group; title-classified rows are labelled as such."""
    data = load_catalogue()
    assert (data.category_group == "Other").mean() < .01
    assert set(data.category_source) == {"source_tree", "title_keywords"}
    assert data[data.category_source == "title_keywords"].category_path.str.count(" > ").eq(0).all()


def test_variant_and_brand_recovered_from_source_text():
    """Variant details come from specifications, description codes or Amazon's bracketed suffix."""
    specs = '{"product_specification"=>[{"key"=>"Brand", "value"=>"X"}, {"key"=>"Model ID", "value"=>"AB12"}, ' \
            '{"key"=>"Color", "value"=>"Black"}]}'
    assert flipkart_variant(specs, "") == "AB12 · Black"
    assert flipkart_variant("", "Notebook Model id NB00664 Type Notebook") == "NB00664"
    assert amazon_variant("Wayona Cable for iPhone (3 FT Pack of 1, Grey)") == "3 FT Pack of 1, Grey"
    data = load_catalogue()
    assert (data.brand == "").sum() < 10
    assert (data[data.platform == "flipkart"].variant != "").mean() > .9
