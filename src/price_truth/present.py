"""Plain-language presentation of computed results; no new numbers are created here."""
import json
import math
from pathlib import Path

# Each verdict: (title, explanation, tone). Tone selects colour and icon; text alone carries meaning.
ASSESSMENT = {
    "below_model_range": ("Lower than expected",
                          "This price is below the range similar historical listings sold for. "
                          "By historical standards it is a good price.", "good"),
    "within_model_range": ("In line with similar listings",
                           "This price sits inside the range similar historical listings sold for.", "neutral"),
    "above_model_range": ("Higher than expected",
                          "This price is above the range similar historical listings sold for. "
                          "The advertised discount may overstate the saving.", "bad"),
    "limited_support": ("Not enough comparable listings",
                        "Fewer than 30 training listings share this platform and category, "
                        "so the estimate is shown without a verdict.", "muted"),
}

TIMING = {
    "below_usual": ("Below the usual price", "Your quote is under the lower quartile of observed prices.", "good"),
    "within_usual": ("Around the usual price", "Your quote is between the lower and upper quartiles.", "neutral"),
    "above_usual": ("Above the usual price", "Your quote is over the upper quartile of observed prices.", "bad"),
    "limited_history": ("History too thin for a signal",
                        "The history is stale or covers fewer than 14 days.", "muted"),
    "insufficient_history": ("Not enough history yet",
                             "At least five earlier observation dates are needed.", "muted"),
}

FORECAST = {
    "evaluated": ("Forecast available", "The selected method beat the last-price baseline on later held-out days.",
                  "good"),
    "baseline_preferred": ("No forecast: last price is as good",
                           "No method beat simply repeating the last price, so no estimate is shown.", "muted"),
    "insufficient_history": ("Not enough history yet",
                             "Forecasts need at least 40 consecutive daily observations.", "muted"),
    "irregular_history": ("Gaps in the history",
                          "Missing days are never filled in, so a forecast cannot be tested.", "muted"),
    "stale_history": ("History is out of date",
                      "The latest observation must be from today or yesterday.", "muted"),
    "invalid_history": ("History cannot be used", "Dates must be unique and prices positive.", "bad"),
}

FEATURES = {
    "log_listed_price": "Listed (MRP) price",
    "rating": "Customer rating",
    "log_rating_count": "Number of ratings",
    "missingindicator_rating": "Rating unavailable",
    "missingindicator_log_rating_count": "Rating count unavailable",
    "price_ratio": "Price compared with MRP",
    "claimed_discount_pct": "Size of the claimed discount",
}


def verdict(table: dict, status: str) -> tuple[str, str, str]:
    """Look up a status, falling back to a readable neutral form for unknown codes."""
    return table.get(status, (status.replace("_", " ").capitalize(), "", "neutral"))


def readable_feature(name: str) -> str:
    """Translate encoded model feature names into labels a shopper can read."""
    if name in FEATURES:
        return FEATURES[name]
    for prefix, label in [("platform_", "Platform"), ("category_group_", "Category"),
                          ("subcategory_", "Subcategory")]:
        if name.startswith(prefix):
            value = name[len(prefix):]
            if value == "infrequent_sklearn":
                value = "rare subcategory"
            value = value.split(" > ")[-1]
            return f"{label}: {value.title() if prefix == 'platform_' else value}"
    return name.replace("_", " ")


GROUPS = [("platform_", "Platform", "platform"), ("category_group_", "Category", "category_group"),
          ("subcategory_", "Subcategory", "subcategory"), ("in_sale_event_", "Sale period", "in_sale_event")]


def feature_group(name: str, listing: dict) -> str:
    """Merge one-hot columns and missing-value flags into the attribute they encode.

    Encoded columns for values this listing does not have still carry SHAP contributions; summing a
    family keeps the explanation additive while naming only the listing's own value.
    """
    for prefix, label, field in GROUPS:
        if name.startswith(prefix):
            value = str(listing.get(field) or "unknown").split(" > ")[-1]
            return f"{label}: {value.title() if field == 'platform' else value}"
    if name in ("rating", "missingindicator_rating"):
        return "Customer rating"
    if name in ("log_rating_count", "missingindicator_log_rating_count"):
        return "Number of ratings"
    return readable_feature(name)


def shap_effects(result: dict, listing: dict | None = None, top: int = 6) -> dict:
    """Express log-space SHAP values as percentage effects on the estimated price.

    The model target is log(1 + price), so each contribution multiplies (1 + price) by exp(value).
    Starting from the baseline, applying every factor reproduces the model estimate exactly.
    """
    totals: dict[str, float] = {}
    for item in result["shap"]:
        label = feature_group(item["feature"], listing or {})
        totals[label] = totals.get(label, 0.) + item["contribution"]
    items = sorted(((k, v) for k, v in totals.items() if abs(v) > 1e-12), key=lambda x: abs(x[1]), reverse=True)
    shown, rest = items[:top], sum(value for _, value in items[top:])
    effects = [{"label": label, "effect_pct": 100 * math.expm1(value)} for label, value in shown]
    if abs(rest) > 1e-12:
        effects.append({"label": "All other factors", "effect_pct": 100 * math.expm1(rest)})
    return {"baseline": math.expm1(result["base_log"]), "estimate": result["estimate"], "effects": effects}


def top_contributions(contributions: list[dict], listing: dict, top: int = 6) -> list[dict]:
    """Group classifier contributions by attribute and keep the largest, signed (log-odds units)."""
    totals: dict[str, float] = {}
    for item in contributions:
        label = feature_group(item["feature"], listing)
        if label.startswith("Sale period"):
            label = "Sale period"
        totals[label] = totals.get(label, 0.) + item["contribution"]
    items = sorted(((k, v) for k, v in totals.items() if abs(v) > 1e-9), key=lambda x: abs(x[1]), reverse=True)
    return [{"label": k, "value": v} for k, v in items[:top]]


SHORT_VERDICT = {"below_model_range": "Below expected", "within_model_range": "As expected",
                 "above_model_range": "Above expected", "limited_support": "No verdict"}


def basis_note(result: dict) -> str:
    """Which comparable listings the verdict rests on, in one sentence."""
    basis = result.get("comparison_basis", "subcategory")
    if basis == "subcategory":
        return f"Compared with {result['support']:,} training listings in the same platform and subcategory."
    if basis == "category":
        return (f"Only {result['support']} training listings share this exact subcategory, so it is compared with "
                f"{result['group_support']:,} in the same platform and category: treat it as a rough guide.")
    return "Too few comparable training listings for a verdict."


def price_card(result: dict) -> dict:
    """Headline card for the price-position verdict."""
    title, text, tone = verdict(ASSESSMENT, result["status"])
    note = "rough guide (category level)" if result.get("comparison_basis") == "category" else title
    return {"label": "Price verdict", "value": SHORT_VERDICT.get(result["status"], title), "tone": tone,
            "note": note, "tip": f"{text} {basis_note(result)}"}


def estimate_card(result: dict) -> dict:
    """Headline card for the model's estimate and its calibrated range."""
    return {"label": "Fair price estimate", "value": money(result["estimate"]),
            "note": f"range {money(result['lower'])}–{money(result['upper'])}",
            "tip": "What similar Amazon and Flipkart listings sold for, from a gradient-boosting model trained on "
                   "real listings. The range holds 90% of held-out selling prices."}


def discount_card(check: dict) -> dict:
    """Headline card comparing the advertised discount with the product's usual one."""
    gap = check["claimed_discount_pct"] - check["usual_discount_pct"]
    return {"label": "Advertised discount", "value": f"{check['claimed_discount_pct']:.0f}% off",
            "tone": "bad" if check["inflated"] else "neutral",
            "note": f"usual {check['usual_discount_pct']:.0f}% ({gap:+.0f} pts)",
            "tip": "Discount off the listed MRP, compared with the median discount this product carried over the "
                   "previous 90 days."}


def saving_card(check: dict) -> dict:
    """Headline card for the real saving against the 30-day lowest price."""
    real = check["real_discount_pct"]
    tone = "bad" if check["inflated"] else "good" if real >= 5 else "muted"
    return {"label": "Real saving", "value": f"{real:.0f}%", "tone": tone,
            "note": f"vs 30-day low {money(check['lowest_30d'])}",
            "tip": "How far the price sits below its lowest price in the 30 days before the promotion "
                   "(the EU Omnibus reference-price rule). Negative means it is above that low."}


def risk_card(risk: dict | None) -> dict:
    """Headline card for the discount-authenticity classifier."""
    if risk is None:
        return {"label": "Inflation risk", "value": "—", "tone": "muted", "note": "model not trained",
                "tip": "The discount-authenticity model is not available in this build."}
    flagged = risk["flagged"]
    return {"label": "Inflation risk", "value": f"{risk['probability_inflated']:.0%}",
            "tone": "bad" if flagged else "good",
            "note": "flagged" if flagged else f"below the {risk['threshold']:.0%} flag line",
            "tip": "Classifier estimate that this discount is inflated, judged only from what a shopper sees on "
                   "the listing. Trained on research-calibrated simulated offers (ROC AUC 0.88 on unseen products)."}


def best_offer_card(offers, platform: str) -> dict:
    """Headline card for the cheapest available platform, including delivery and fees."""
    available = offers[offers.available]
    if available.empty:
        return {"label": "Best place to buy", "value": "—", "tone": "muted", "note": "not available today",
                "tip": "No platform lists this product today."}
    best = available.iloc[0]
    own = offers[offers.platform.str.lower() == platform]
    saving = float(own.total.iloc[0] - best.total) if not own.empty else 0.0
    note = f"saves {money(saving)} incl. delivery" if saving > 0 else "incl. delivery and fees"
    return {"label": "Best place to buy", "value": f"{best.platform} {money(best.total)}", "tone": "good",
            "note": note, "tip": "Lowest total cost (price + delivery + platform fee) across up to 8 Indian "
                                 "platforms that sell this category. Offers are simulated from the listing's price."}


def kpi_cards(result: dict, check: dict, risk: dict | None, offers, platform: str) -> list[dict]:
    """The six headline figures shown at the top of the dashboard, in reading order."""
    return [price_card(result), estimate_card(result), discount_card(check), saving_card(check),
            risk_card(risk), best_offer_card(offers, platform)]


def money(value: float, currency: str = "INR") -> str:
    """Format an amount with the rupee sign for INR and a code otherwise."""
    if currency == "INR":
        return f"₹{value:,.0f}" if value >= 100 else f"₹{value:,.2f}"
    return f"{currency} {value:,.2f}"


def category_quality(audit_path: Path, platform: str, category: str) -> dict | None:
    """Return held-out quality for this platform/category when it is weak (R² below 0.5)."""
    try:
        groups = json.loads(audit_path.read_bytes())["subgroups"]
    except (OSError, ValueError, KeyError):
        return None
    for group in groups:
        if group["platform"] == platform and group["category"] == category and group["r2"] < .5:
            return group
    return None
