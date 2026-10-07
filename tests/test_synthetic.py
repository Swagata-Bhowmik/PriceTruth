"""The seeded generator, labelling rule and discount classifier behave as documented."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from price_truth import authenticity, synthetic

LISTING = {"key": "test:001", "platform": "flipkart", "category_group": "Clothing", "listed_price": 1000.,
           "selling_price": 600., "name": "Test shirt", "rating": 4.1, "rating_count": 10}


def test_history_is_deterministic_and_stable_over_time():
    """The same key gives the same prices, and extending the end date never rewrites the past."""
    early = synthetic.price_history(LISTING, date(2025, 6, 30))
    later = synthetic.price_history(LISTING, date(2025, 12, 31))
    assert early.equals(synthetic.price_history(LISTING, date(2025, 6, 30)))
    assert later.iloc[:len(early)].reset_index(drop=True).equals(early)
    other = synthetic.price_history({**LISTING, "key": "test:002"}, date(2025, 6, 30))
    assert not np.array_equal(other.price.to_numpy(), early.price.to_numpy())


def test_history_is_consecutive_daily_positive_and_labelled():
    """Every day is present once, prices are positive retail values and rows say they are synthetic."""
    history = synthetic.price_history(LISTING, date(2025, 3, 1))
    assert history.date.diff().dropna().eq(pd.Timedelta(days=1)).all()
    assert (history.price > 0).all() and (history.mrp >= history.price).all()
    assert history.provenance.eq("synthetic").all()
    high = history.price[history.price >= 100]
    assert (high % 10 == 9).all()


def test_history_is_anchored_to_the_real_catalogue_price():
    """On the anchor date the regular price equals the listing's real selling price (before sales/noise)."""
    history = synthetic.price_history(LISTING, date(2026, 6, 1))
    anchor = pd.Timestamp(synthetic.assumptions()["dynamics"]["anchor_date"])
    nearby = history[(history.date - anchor).abs() <= pd.Timedelta(days=10)]
    assert nearby.price.median() == pytest.approx(LISTING["selling_price"], rel=.25)


def test_sale_events_follow_the_platform_calendar():
    """Sale-event days come only from events listed for this platform."""
    names = set(synthetic.price_history(LISTING, date(2026, 6, 1)).event) - {""}
    allowed = {e["name"] for e in synthetic.assumptions()["sale_events"]
               if "flipkart" in e["platforms"] or "all" in e["platforms"]}
    assert names and names <= allowed


def history(prices, mrps, events=None):
    """Hand-made daily history for exercising the labelling rule."""
    days = pd.date_range("2025-01-01", periods=len(prices))
    return pd.DataFrame({"date": days, "price": prices, "mrp": mrps, "event": events or [""] * len(prices)})


def test_rule_flags_a_bigger_discount_without_a_real_price_drop():
    """Raising MRP to advertise a bigger discount, at an unchanged price, is inflated."""
    frame = history([500.] * 100, [1000.] * 99 + [1500.])
    check = synthetic.reference_check(frame, 500., 1500.)
    assert check["usual_discount_pct"] == pytest.approx(50)
    assert check["inflated"] and check["real_discount_pct"] == pytest.approx(0)


def test_rule_accepts_a_real_price_drop_and_a_usual_discount():
    """A genuine cut below the 30-day low is fine; so is the usual MRP discount."""
    frame = history([500.] * 99 + [400.], [1000.] * 100)
    assert not synthetic.reference_check(frame, 400., 1000.)["inflated"]
    assert not synthetic.reference_check(history([500.] * 100, [1000.] * 100), 500., 1000.)["inflated"]


def test_rule_uses_prices_from_before_the_promotion():
    """On day three of a sale, earlier sale days are not the reference (Omnibus principle)."""
    prices = [500.] * 97 + [400.] * 3
    frame = history(prices, [1000.] * 100, [""] * 97 + ["Sale"] * 3)
    check = synthetic.reference_check(frame, 400., 1000.)
    assert check["lowest_30d"] == 500. and check["real_discount_pct"] == pytest.approx(20)
    with pytest.raises(ValueError):
        synthetic.reference_check(history([500.], [1000.], ["Sale"]), 500., 1000.)


def test_labelled_examples_cover_sale_days_and_mark_inflators():
    """Samples include event days; inflating sellers dominate the positive labels."""
    rows = pd.concat([synthetic.labelled_examples({**LISTING, "key": f"test:{i}"}, 10, date(2026, 6, 1))
                      for i in range(60)])
    assert rows.in_sale_event.any() and rows.provenance.eq("synthetic").all()
    assert rows.inflated.mean() < .5


def test_offers_rank_by_total_cost_and_include_own_platform():
    """The listing's platform uses its own history price; offers are sorted by availability then total."""
    offers = synthetic.offers_for(LISTING, date(2026, 6, 1))
    own = offers[offers.platform.str.lower() == "flipkart"].iloc[0]
    assert own.price == synthetic.price_history(LISTING, date(2026, 6, 1)).price.iloc[-1]
    available = offers[offers.available]
    assert available.total.is_monotonic_increasing
    assert (offers.total == offers.price + offers.delivery_fee + offers.platform_fee).all()
    assert offers.link.str.startswith("https://").all()


def test_food_history_is_anchored_and_shaped_like_open_prices():
    """Simulated shop prices use the Open Prices schema and stay near the real anchor price."""
    frame = synthetic.food_history("8901234567890", "Test food", 50., 900001, date(2025, 12, 31))
    assert {"product_code", "location_id", "price_per", "proof_id", "location_type"} <= set(frame.columns)
    assert frame.provenance.eq("synthetic").all() and frame.location_type.eq("shop").all()
    assert 25 < frame.price.median() < 100


def test_next_event_is_in_the_future():
    """The upcoming-sale helper returns a positive number of days or None after the calendar ends."""
    upcoming = synthetic.days_until_next_event("flipkart", date(2025, 1, 1))
    assert upcoming is None or upcoming[1] > 0
    assert synthetic.days_until_next_event("flipkart", synthetic.HORIZON + timedelta(days=1)) is None


def test_classifier_trains_reports_and_explains(tmp_path, monkeypatch):
    """Group-split training produces metrics, a tuned threshold and per-feature contributions."""
    monkeypatch.setattr(authenticity, "MODEL", tmp_path / "model.joblib")
    monkeypatch.setattr(authenticity, "REPORTS", tmp_path)
    rows = pd.concat([synthetic.labelled_examples({**LISTING, "key": f"test:{i}",
                                                    "category_group": ["Clothing", "Electronics"][i % 2]},
                                                   10, date(2026, 6, 1)) for i in range(120)])
    report = authenticity.train(rows)
    assert 0 <= report["threshold"] <= 1 and report["test"]["roc_auc"] > .5
    bundle = authenticity.load()
    result = authenticity.assess_discount(bundle, LISTING, 600., 1000., True)
    assert 0 <= result["probability_inflated"] <= 1
    assert result["contributions"] and isinstance(result["flagged"], bool | np.bool_)


def test_price_level_factor_uses_official_cpi():
    """Flipkart 2016 prices scale by about 1.5; Amazon Jan 2023 by about 1.09; unknown dates are unscaled."""
    level = synthetic.assumptions()["price_level"]
    general = level["general_index"]
    flipkart = {**LISTING, "observed_at": "2016-05-10T00:00:00+00:00", "category_group": "Jewellery"}
    assert synthetic.price_level_factor(flipkart) == pytest.approx(general["2025-05"] / general["2016-05"])
    clothing = synthetic.price_level_factor({**flipkart, "category_group": "Clothing"})
    assert clothing == pytest.approx(198.0 / 132.2)  # full May 2016 → May 2025 sub-group change
    amazon = synthetic.price_level_factor({**LISTING, "platform": "amazon", "observed_at": "2023-01-05",
                                          "category_group": "Personal care"})
    assert amazon == pytest.approx(193.0 / 176.5)
    assert synthetic.price_level_factor({**LISTING, "observed_at": ""}) == 1.0


def test_history_starts_from_the_inflation_adjusted_price():
    """A 2016 listing's simulated regular price sits near its CPI-adjusted level, not its 2016 price."""
    old = {**LISTING, "observed_at": "2016-05-10T00:00:00+00:00"}
    factor = synthetic.price_level_factor(old)
    history = synthetic.price_history(old, date(2026, 6, 1))
    anchor = pd.Timestamp(synthetic.assumptions()["dynamics"]["anchor_date"])
    nearby = history[(history.date - anchor).abs() <= pd.Timedelta(days=10)]
    assert nearby.price.median() == pytest.approx(LISTING["selling_price"] * factor, rel=.25)
