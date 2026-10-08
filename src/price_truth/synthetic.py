"""Seeded synthetic price data calibrated to researched Indian e-commerce patterns.

Every generated row carries provenance="synthetic". Generation is deterministic per product key:
a fixed calendar (START..HORIZON) is simulated once and truncated to the requested end date, so
past days never change as time passes and the app, dataset files and tests agree exactly.
Parameters and their sources live in datasets/final/assumptions.json.
"""
import hashlib
import json
from datetime import date, timedelta
from functools import lru_cache
from urllib.parse import quote_plus

import numpy as np
import pandas as pd

from price_truth.paths import DATA

ASSUMPTIONS = DATA / "final" / "assumptions.json"
START, HORIZON = date(2024, 1, 1), date(2027, 12, 31)
DAYS = pd.date_range(START, HORIZON, freq="D")


@lru_cache(maxsize=1)
def assumptions() -> dict:
    """Load the researched generator parameters."""
    return json.loads(ASSUMPTIONS.read_bytes())


def seed_for(*parts: str) -> int:
    """Stable 64-bit seed from text, independent of Python's hash randomisation."""
    return int.from_bytes(hashlib.sha256("|".join(parts).encode()).digest()[:8], "little")


def category_params(category: str) -> dict:
    """Category settings, falling back to the 'Other' profile."""
    table = assumptions()["categories"]
    return table.get(category, table["Other"])


@lru_cache(maxsize=16)
def sale_mask(platform: str) -> np.ndarray:
    """Per-day sale-event name for a platform over the full simulated calendar ('' when none)."""
    names = np.full(len(DAYS), "", dtype=object)
    for event in assumptions()["sale_events"]:
        if platform not in event["platforms"] and "all" not in event["platforms"]:
            continue
        start, end = pd.Timestamp(event["start"]), pd.Timestamp(event["end"])
        names[(DAYS >= start) & (DAYS <= end)] = event["name"]
    names.flags.writeable = False
    return names


def _charm(prices: np.ndarray) -> np.ndarray:
    """Round like retail prices: whole rupees, ending in 9 above ₹100."""
    rounded = np.round(prices)
    high = rounded >= 100
    rounded[high] = np.floor(rounded[high] / 10) * 10 + 9
    return np.maximum(rounded, 1.0)


def _regular_path(rng: np.random.Generator, anchor: float, params: dict, dynamics: dict) -> np.ndarray:
    """Step changes at random revision dates plus annual inflation drift."""
    n = len(DAYS)
    revisions = rng.random(n) < 1 / params["mean_days_between_revisions"]
    steps = np.where(revisions, rng.normal(0, params["revision_sd"], n), 0.0)
    drift = np.log1p(dynamics["annual_inflation"]) / 365
    path = np.exp(np.cumsum(steps + drift))
    return anchor * path / path[(pd.Timestamp(dynamics["anchor_date"]) - DAYS[0]).days]


def _sales(rng, regular, mrp, events, params, inflator, dynamics):
    """Apply event discounts; inflating sellers raise price and MRP before and during events."""
    price, shown_mrp = regular.copy(), mrp.copy()
    in_event = events != ""
    starts = np.flatnonzero(in_event & ~np.r_[False, in_event[:-1]])
    for start in starts:
        end = start
        while end + 1 < len(events) and events[end + 1] == events[start]:
            end += 1
        depth = rng.uniform(*params["sale_extra_discount"])
        if inflator:
            lead = int(rng.integers(*dynamics["inflation_lead_days"]))
            bump = rng.uniform(*dynamics["pre_sale_markup"])
            price[max(0, start - lead):start] *= 1 + bump
            shown_mrp[start:end + 1] *= 1 + rng.uniform(*dynamics["inflated_mrp_markup"])
            depth *= dynamics["inflator_real_discount_share"]
        price[start:end + 1] = regular[start:end + 1] * (1 - depth)
    return price, shown_mrp


def price_level_factor(listing: dict) -> float:
    """CPI scaling from the listing's crawl month to the anchor month (1.0 when the date is unknown)."""
    level = assumptions()["price_level"]
    general = level["general_index"]
    observed = str(listing.get("observed_at") or "")[:7]
    if observed not in general:
        return 1.0
    anchor = level["anchor_month"]
    subgroup = level["subgroups"][level["category_subgroup"].get(listing["category_group"], "general")]
    base = level["subgroups"]["general"]
    drift = (subgroup["may_2025"] / subgroup["may_2016"]) / (base["may_2025"] / base["may_2016"])
    months = (pd.Period(anchor, "M") - pd.Period(observed, "M")).n
    return general[anchor] / general[observed] * drift ** (months / 108)


def full_history(listing: dict) -> pd.DataFrame:
    """Simulate the whole calendar for one listing (cached by key in callers)."""
    params, dynamics = category_params(listing["category_group"]), assumptions()["dynamics"]
    rng = np.random.default_rng(seed_for(listing["key"], "history"))
    shares = assumptions()["inflator_share_by_platform"]
    inflator = rng.random() < shares.get(listing["platform"], shares["default"]) * params["inflator_weight"]
    regular = _regular_path(rng, float(listing["selling_price"]) * price_level_factor(listing), params, dynamics)
    mrp = np.maximum(float(listing["listed_price"]) * regular / float(listing["selling_price"]), regular)
    events = sale_mask(listing["platform"])
    price, shown_mrp = _sales(rng, regular, mrp, events, params, inflator, dynamics)
    wobble = rng.random(len(DAYS)) < dynamics["daily_change_probability"]
    price = price * np.where(wobble, 1 + rng.normal(0, dynamics["daily_change_sd"], len(DAYS)), 1.0)
    price = _charm(price)
    shown_mrp = np.maximum(_charm(shown_mrp), price)
    return pd.DataFrame({"date": DAYS, "price": price, "mrp": shown_mrp, "event": events,
                         "key": listing["key"], "inflating_seller": inflator, "provenance": "synthetic"})


def price_history(listing: dict, end: date | None = None, days: int | None = None) -> pd.DataFrame:
    """Daily simulated prices for a listing up to `end` (default today), optionally the last `days`."""
    end = min(end or date.today(), HORIZON)
    frame = full_history(listing)
    frame = frame[frame.date <= pd.Timestamp(end)]
    return frame.tail(days).reset_index(drop=True) if days else frame.reset_index(drop=True)


def reference_check(history: pd.DataFrame, price: float, mrp: float) -> dict:
    """Is a bigger-than-usual discount being advertised without a real price drop?

    Uses the 30-day lowest price as the fair reference (EU Omnibus principle) and the product's
    usual MRP-based discount over the previous 90 days, because Indian listings quote discounts
    against MRP, which normally sits well above the selling price.
    """
    rules = assumptions()["labels"]
    prior = history.iloc[:-1]
    if "event" in history and history.event.iloc[-1]:
        # Omnibus reference: the lowest price before the current promotion began.
        running = history.event.iloc[:-1][::-1]
        same = running.eq(history.event.iloc[-1]).cumprod().sum()
        prior = prior.iloc[:len(prior) - int(same)]
    if prior.empty:
        raise ValueError("Need at least one earlier day to establish a reference price.")
    lowest = float(prior.price.tail(30).min())
    recent = prior.tail(90)
    usual = float(np.median(100 * (1 - recent.price / recent.mrp)))
    claimed = 100 * (1 - price / mrp)
    real = 100 * (1 - price / lowest)
    inflated = claimed - usual >= rules["threshold_pp"] and real < rules["min_real_saving_pct"]
    return {"claimed_discount_pct": claimed, "usual_discount_pct": usual, "lowest_30d": lowest,
            "real_discount_pct": real, "inflated": bool(inflated)}


def labelled_examples(listing: dict, samples: int, end: date) -> pd.DataFrame:
    """Sample days from one history and label each advertised discount with the reference rule."""
    history = price_history(listing, end)
    rng = np.random.default_rng(seed_for(listing["key"], "labels"))
    candidates = np.arange(31, len(history))
    event_days = candidates[history.event.iloc[candidates].ne("").to_numpy()]
    picks = np.unique(np.r_[rng.choice(candidates, samples, replace=False),
                            rng.choice(event_days, min(len(event_days), samples // 2), replace=False)])
    rows = []
    for index in picks:
        window = history.iloc[:index + 1]
        day = history.iloc[index]
        check = reference_check(window, day.price, day.mrp)
        rows.append({"key": listing["key"], "date": day.date.date().isoformat(), "platform": listing["platform"],
                     "category_group": listing["category_group"], "listed_price": day.mrp, "selling_price": day.price,
                     "claimed_discount_pct": check["claimed_discount_pct"], "in_sale_event": day.event != "",
                     "rating": listing.get("rating"), "rating_count": listing.get("rating_count"),
                     "lowest_30d": check["lowest_30d"], "usual_discount_pct": check["usual_discount_pct"],
                     "real_discount_pct": check["real_discount_pct"],
                     "inflated": check["inflated"], "provenance": "synthetic"})
    return pd.DataFrame(rows)


def offers_for(listing: dict, on: date | None = None) -> pd.DataFrame:
    """Simulated same-product offers on platforms that sell this category, ranked by total cost."""
    on = on or date.today()
    history = price_history(listing, on)
    own_price = float(history.price.iloc[-1])
    rows = []
    for name, platform in assumptions()["platforms"].items():
        if listing["category_group"] not in platform["categories"] and name.lower() != listing["platform"]:
            continue
        rng = np.random.default_rng(seed_for(listing["key"], name, on.isoformat()))
        if name.lower() == listing["platform"]:
            price, available = own_price, True
        else:
            price = float(_charm(np.array([own_price * np.exp(rng.normal(platform["price_log_mean"],
                                                                           platform["price_log_sd"]))]))[0])
            available = rng.random() < platform["availability"]
        delivery = 0.0 if price >= platform["free_delivery_threshold"] else float(platform["delivery_fee"])
        fee = float(platform.get("platform_fee", 0))
        rows.append({"platform": name, "price": price, "delivery_fee": delivery, "platform_fee": fee,
                     "total": price + delivery + fee,
                     "available": available, "link": platform["search_url"].format(q=quote_plus(listing["name"][:80])),
                     "date": on.isoformat(), "provenance": "synthetic" if name.lower() != listing["platform"] else
                     "synthetic_history"})
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["available", "total"], ascending=[False, True]).reset_index(drop=True)
    return frame


def offers_with_quote(listing: dict, price: float, on: date | None = None) -> pd.DataFrame:
    """Offers where the listing's own platform charges the shopper's quoted price (fees recomputed)."""
    offers = offers_for(listing, on)
    own = offers.platform.str.lower() == listing["platform"]
    if not own.any():
        return offers
    platform = assumptions()["platforms"][offers.loc[own, "platform"].iloc[0]]
    delivery = 0.0 if price >= platform["free_delivery_threshold"] else float(platform["delivery_fee"])
    offers.loc[own, ["price", "delivery_fee", "provenance"]] = [float(price), delivery, "user_quote"]
    offers["total"] = offers.price + offers.delivery_fee + offers.platform_fee
    return offers.sort_values(["available", "total"], ascending=[False, True]).reset_index(drop=True)


def food_history(code: str, name: str, anchor_price: float, store: int, end: date | None = None) -> pd.DataFrame:
    """Daily simulated shop prices for a real barcode, anchored at a real observed INR price."""
    params, dynamics = category_params("Grocery"), assumptions()["dynamics"]
    rng = np.random.default_rng(seed_for(code, str(store), "food"))
    regular = _regular_path(rng, anchor_price, params, dynamics)
    wobble = rng.random(len(DAYS)) < dynamics["daily_change_probability"]
    promo = rng.random(len(DAYS)) < params["promo_day_probability"]
    price = regular * np.where(wobble, 1 + rng.normal(0, dynamics["daily_change_sd"], len(DAYS)), 1.0)
    price = np.round(price * np.where(promo, 1 - rng.uniform(*params["sale_extra_discount"], len(DAYS)), 1.0), 2)
    frame = pd.DataFrame({"date": DAYS.date.astype(str), "price": np.maximum(price, .01)})
    frame = frame[pd.to_datetime(frame.date) <= pd.Timestamp(min(end or date.today(), HORIZON))]
    return frame.assign(id=[f"sim-{code}-{store}-{i}" for i in range(len(frame))], product_code=code,
                        product_name=name, currency="INR", price_per="UNIT", price_is_discounted=None,
                        price_without_discount=None, location_id=store,
                        location_name=f"Simulated store {store - 900000}", location_type="shop",
                        proof_id="simulated", duplicate_of=None, source_url=None, provenance="synthetic")


def days_until_next_event(platform: str, on: date | None = None) -> tuple[str, int] | None:
    """Name of the next sale event on the platform's calendar and days until it starts."""
    on = pd.Timestamp(on or date.today())
    upcoming = [(pd.Timestamp(e["start"]), e["name"]) for e in assumptions()["sale_events"]
                if (platform in e["platforms"] or "all" in e["platforms"]) and pd.Timestamp(e["start"]) > on]
    if not upcoming:
        return None
    start, name = min(upcoming)
    return name, (start - on).days


def recent_window(end: date | None = None, days: int = 180) -> tuple[date, date]:
    """Convenience range for charts."""
    end = end or date.today()
    return end - timedelta(days=days), end
