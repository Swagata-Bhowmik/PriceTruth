"""Immutable public-response snapshots; retrieval dates never become observation dates."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from price_truth.cache import read_json, write_json


def archive_snapshot(record: dict, directory: Path) -> Path:
    """Store each distinct response once, retaining corrections and source provenance."""
    if not isinstance(record.get("observations"), list):
        raise ValueError("Snapshot needs an observations list.")
    timestamp = datetime.fromisoformat(record["fetched_at"])
    if timestamp.tzinfo is None or not record.get("source") or not record.get("license"):
        raise ValueError("Snapshot needs an aware timestamp, source and licence.")
    payload = json.dumps(record, sort_keys=True, allow_nan=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    target = directory / f"{digest}.json"
    if not target.exists():
        write_json(target, record)
    return target


def accumulated_observations(directory: Path) -> tuple[pd.DataFrame, dict]:
    """Use the latest revision of each source observation; never create daily repeats."""
    records = []
    for path in sorted(directory.glob("*.json")):
        record = read_json(path)
        if not record or not isinstance(record.get("observations"), list):
            raise ValueError(f"Invalid archived snapshot: {path.name}")
        try:
            retrieved = datetime.fromisoformat(record["fetched_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Archived snapshot without a valid retrieval time: {path.name}") from exc
        if retrieved.tzinfo is None:
            raise ValueError(f"Archived snapshot retrieval time lacks a timezone: {path.name}")
        records.append(record)
    records.sort(key=lambda r: datetime.fromisoformat(r["fetched_at"]))
    by_id = {}
    for record in records:
        for observation in record["observations"]:
            by_id[(record["source"], str(observation["id"]))] = observation
    metadata = {"snapshots": len(records), "unique_source_observations": len(by_id),
                "latest_retrieval": records[-1]["fetched_at"] if records else None,
                "scope": "Latest source revision per observation ID; absent rows are not inferred deletions."}
    return pd.DataFrame(by_id.values()), metadata


def history_readiness(frame: pd.DataFrame) -> pd.DataFrame:
    """Expose true date density and missing basis, separately from model accuracy."""
    if frame.empty:
        return pd.DataFrame()
    from price_truth.forecast import forecast_next_day
    from price_truth.history import series_for

    rows = []
    grouped = frame.assign(price_per=frame.price_per.fillna("UNKNOWN"))
    for identity, _ in grouped.groupby(["product_code", "location_id", "currency", "price_per"]):
        code, store, currency, basis = identity
        series = series_for(frame, code, store, currency, basis)
        forecast = forecast_next_day(series)
        rows.append({"barcode": code, "store": store, "currency": currency, "basis": basis,
                     "distinct_dates": len(series), "history_status": forecast["status"],
                     "basis_known": basis != "UNKNOWN",
                     "pack_continuity": "Not established by barcode alone",
                     "forecast_authorized": False})
    return pd.DataFrame(rows).sort_values("distinct_dates", ascending=False)
