"""Price-history signals restricted to one product, store, currency, and unit."""
import json
from datetime import date

import pandas as pd

from price_truth.calculations import positive
from price_truth.paths import EXTERNAL


def load_observations(example: bool = False) -> tuple[pd.DataFrame, dict]:
    """Load public observed INR prices separately from snapshot training data."""
    filename = "open_prices_example.json" if example else "open_prices_inr.json"
    payload = json.loads((EXTERNAL / filename).read_bytes())
    return pd.DataFrame(payload["observations"]), {k: v for k, v in payload.items() if k != "observations"}


def series_for(frame: pd.DataFrame, code: str, location_id: int, currency: str,
               price_per: str = "UNIT") -> pd.DataFrame:
    """Filter comparable dated observations and collapse same-day repeats to a median."""
    unit = frame.price_per.fillna("UNKNOWN")
    selected = frame[(frame.product_code == code) & (frame.location_id == location_id)
                     & (frame.currency == currency) & (unit == price_per)
                     & frame.duplicate_of.isna() & frame.proof_id.notna()
                     & (frame.location_type == "shop")
                     & (frame.price > 0)].copy()
    selected["date"] = pd.to_datetime(selected.date, errors="coerce")
    selected = selected.dropna(subset=["date"])
    selected = selected[selected.date.dt.date <= date.today()]
    return selected.groupby("date", as_index=False).agg(price=("price", "median"),
                                                        observations=("price", "size"))


def timing_signal(series: pd.DataFrame, current_price: float,
                  today: date | None = None) -> dict:
    """Compare a user's current quote with prior observations, not a seasonal forecast."""
    current_price = positive(current_price)
    today = today or date.today()
    prior = series[pd.to_datetime(series.date).dt.date < today].sort_values("date")
    if len(prior) < 5:
        return {"status": "insufficient_history", "days": len(prior),
                "message": "At least five distinct prior observation dates are needed."}
    age = (today - pd.Timestamp(prior.date.iloc[-1]).date()).days
    span = (pd.Timestamp(prior.date.iloc[-1]) - pd.Timestamp(prior.date.iloc[0])).days
    median = float(prior.price.median())
    low, high = float(prior.price.quantile(.25)), float(prior.price.quantile(.75))
    result = {"days": len(prior), "span_days": span, "age_days": age, "median": median,
              "q25": low, "q75": high, "difference_from_median_pct": 100 * (current_price / median - 1)}
    if age > 90 or span < 14:
        return {**result, "status": "limited_history",
                "message": "History is stale or spans fewer than 14 days; no buy/wait signal."}
    status = "below_usual" if current_price < low else "above_usual" if current_price > high else "within_usual"
    return {**result, "status": status,
            "message": "Comparison with observed prices only. Future prices and sale dates are unknown."}
