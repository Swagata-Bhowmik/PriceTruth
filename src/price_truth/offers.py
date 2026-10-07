"""Compare recent user-evidenced quotes for exactly one product and normalized pack."""
from datetime import date

import numpy as np
import pandas as pd

from price_truth.calculations import UNITS
from price_truth.observations import validate_observations


def require_same_pack(data: pd.DataFrame) -> None:
    """All quotes must measure the same dimension and the same total quantity."""
    dimensions = {UNITS[u][0] for u in data.unit}
    quantities = np.array([q*UNITS[u][1] for q, u in zip(data.quantity, data.unit, strict=True)])
    if len(dimensions) != 1 or not np.isclose(quantities, quantities[0], rtol=1e-9, atol=0).all():
        raise ValueError("Quotes must refer to the same total pack quantity and dimension.")


def compare_observed_offers(frame: pd.DataFrame, confirmed: bool = False,
                            today: date | None = None) -> pd.DataFrame:
    """Rank like-for-like quotes only; never imply verified availability or completeness."""
    if not confirmed:
        raise ValueError("Confirm identical product/pack and the same tax, delivery and purchase conditions.")
    today = today or date.today()
    data = validate_observations(frame, today=today)
    if len(data[["product_id", "variant", "currency"]].drop_duplicates()) != 1:
        raise ValueError("Select exactly one product, variant and currency.")
    data["age_days"] = (pd.Timestamp(today)-pd.to_datetime(data.date)).dt.days
    data = data[data.age_days <= 1]  # only recent quotes are ranked, so only they must share a pack size
    if data.empty:
        raise ValueError("Need at least two stores with quotes dated today or yesterday.")
    require_same_pack(data)
    latest = data.groupby("store").date.transform("max")
    data = data[data.date == latest]
    if data.groupby("store").price.nunique().gt(1).any():
        raise ValueError("Reconcile conflicting latest prices for a store before ranking quotes.")
    data = data.sort_values(["store", "source_url"]).drop_duplicates("store")
    if data.store.nunique() < 2:
        raise ValueError("Need at least two stores with quotes dated today or yesterday.")
    data = data.sort_values(["price", "store"]).reset_index(drop=True)
    data["price_rank"] = data.price.rank(method="dense").astype(int)
    data["scope"] = "Recent user-supplied quotes; availability and completeness unverified"
    return data[["price_rank", "store", "price", "currency", "date", "age_days", "source_url", "scope"]]
