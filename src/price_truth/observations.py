"""Validated user-supplied evidence; never silently promoted to verified market data."""
import io
import re
from datetime import date
from urllib.parse import urlparse

import pandas as pd

from price_truth.calculations import UNITS, positive, shrink_change, unit_price

COLUMNS = ["product_id", "name", "variant", "store", "currency", "date", "price",
           "quantity", "unit", "source_url"]
IDENTITY = ["product_id", "variant", "store", "currency", "unit", "quantity"]
MAX_BYTES = 2_000_000
MAX_ROWS = 10_000


def evidence_url(value: str) -> str:
    """Validate a source link without fetching arbitrary user-controlled URLs."""
    value = str(value).strip()
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or any(c.isspace() for c in value)):
        raise ValueError("Each source must be an HTTPS link without credentials or spaces.")
    return value


TEXT_COLUMNS = ["product_id", "name", "variant", "store", "currency", "unit"]
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def _require_shape(frame: pd.DataFrame) -> None:
    """Reject missing columns and empty or oversized imports before any parsing."""
    if not set(COLUMNS).issubset(frame.columns):
        raise ValueError("Required columns: " + ", ".join(COLUMNS))
    if frame.empty or len(frame) > MAX_ROWS:
        raise ValueError(f"Supply between 1 and {MAX_ROWS:,} observations.")


def _clean_text(out: pd.DataFrame) -> None:
    """Strip identity text, then normalize and check currency codes and units in place."""
    for column in TEXT_COLUMNS:
        out[column] = out[column].fillna("").astype(str).str.strip()
        if out[column].eq("").any() or out[column].str.len().gt(200).any():
            raise ValueError(f"{column}: supply non-empty text of at most 200 characters.")
    out["currency"] = out.currency.str.upper()
    out["unit"] = out.unit.str.lower()
    if not out.currency.str.fullmatch(r"[A-Z]{3}").all():
        raise ValueError("Currency must be a three-letter code, for example INR.")
    if not out.unit.isin(UNITS).all():
        raise ValueError("Units must be g, kg, ml, l or count.")


def _clean_dates(dates: pd.Series, today: date) -> pd.Series:
    """Accept only strict ISO calendar dates that are not after today."""
    raw_dates = dates.astype(str)
    if not raw_dates.map(lambda v: bool(DATE_PATTERN.fullmatch(v))).all():
        raise ValueError("Dates must use YYYY-MM-DD.")
    parsed = pd.to_datetime(raw_dates, errors="coerce")
    if parsed.isna().any() or (parsed.dt.date > today).any():
        raise ValueError("Dates must be valid and cannot be in the future.")
    return parsed.dt.strftime("%Y-%m-%d")


def _clean_amounts(out: pd.DataFrame) -> None:
    """Convert prices and quantities to finite positive floats in place."""
    try:
        out["price"] = out.price.map(positive)
        out["quantity"] = out.quantity.map(positive)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Prices and quantities must be finite positive numbers.") from exc


def validate_observations(frame: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """Validate an entire import before returning it; no partial ingestion or fuzzy identity."""
    _require_shape(frame)
    out = frame[COLUMNS].copy()
    _clean_text(out)
    out["date"] = _clean_dates(out.date, today or date.today())
    _clean_amounts(out)
    out["source_url"] = out.source_url.map(evidence_url)
    if out.groupby("product_id").name.nunique().gt(1).any():
        raise ValueError("One product ID cannot have conflicting names within an import.")
    out = out.drop_duplicates().sort_values(IDENTITY + ["date"]).reset_index(drop=True)
    out["provenance"] = "user_supplied_unverified"
    return out


def read_csv(payload: bytes) -> pd.DataFrame:
    """Bound upload size and preserve leading zeros in product IDs."""
    if len(payload) > MAX_BYTES:
        raise ValueError("CSV must be at most 2 MB.")
    try:
        frame = pd.read_csv(io.BytesIO(payload), dtype=str, nrows=MAX_ROWS + 1)
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError("Upload a UTF-8 CSV with the documented columns.") from exc
    return validate_observations(frame)


def daily_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Require one explicit comparable pack/store identity, then median same-day quotes."""
    if frame[IDENTITY].drop_duplicates().shape[0] != 1:
        raise ValueError("Select one product, variant, store, currency, unit and pack quantity.")
    out = frame.assign(date=pd.to_datetime(frame.date))
    return out.groupby("date", as_index=False).agg(price=("price", "median"),
                                                   observations=("price", "size"))


def pack_changes(frame: pd.DataFrame, confirmed_same_variant: bool = False) -> pd.DataFrame:
    """Compare dated user evidence only after explicit confirmation of product continuity."""
    if not confirmed_same_variant:
        raise ValueError("Confirm these records describe the same product variant over time.")
    identity = ["product_id", "variant", "store", "currency"]
    if frame.empty or frame[identity].drop_duplicates().shape[0] != 1:
        raise ValueError("Select one product variant, store and currency.")
    dimensions = {UNITS[u][0] for u in frame.unit}
    if len(dimensions) != 1:
        raise ValueError("Mass, volume and count observations cannot be mixed.")
    comparable = frame.assign(normalized_quantity=[q * UNITS[u][1] for q, u in zip(frame.quantity, frame.unit, strict=True)])
    if comparable.groupby("date").normalized_quantity.nunique().gt(1).any():
        raise ValueError("Multiple sizes on one date may be pack variants, not a size change.")
    if frame.groupby("date").price.nunique().gt(1).any():
        raise ValueError("Conflicting same-day prices need reconciliation before pack-change analysis.")
    ordered = frame.sort_values("date").drop_duplicates("date").to_dict("records")
    changes = []
    for before, after in zip(ordered, ordered[1:], strict=False):
        old = before["quantity"] * UNITS[before["unit"]][1]
        new = after["quantity"] * UNITS[after["unit"]][1]
        changes.append({"from_date": before["date"], "to_date": after["date"],
                        **shrink_change(old, new, before["price"], after["price"]),
                        "new_unit_price": unit_price(after["price"], after["quantity"], after["unit"])["value"],
                        "before_source": before["source_url"], "after_source": after["source_url"],
                        "evidence": "User-supplied; continuity confirmed by uploader, not independently verified"})
    return pd.DataFrame(changes)
