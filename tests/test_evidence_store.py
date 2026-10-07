"""Collection integrity checks; controlled fixtures never become shipped observations."""
import hashlib
import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from price_truth.cache import write_json
from price_truth.evidence_store import accumulated_observations, archive_snapshot, history_readiness
from price_truth.price_api import fetch_observations


def snapshot(retrieved="2026-01-02T00:00:00+00:00", price=10):
    """A clearly labelled test-only observation with no contributor identity."""
    return {"source": "https://example.com/test-prices", "license": "test fixture",
            "fetched_at": retrieved, "observations": [
                {"id": 1, "product_code": "00001234", "location_id": 1, "currency": "INR",
                 "price_per": "UNIT", "date": "2026-01-01", "price": price,
                 "duplicate_of": None, "proof_id": 1, "location_type": "shop"}]}


def test_repeated_collection_never_manufactures_history(tmp_path):
    """Repeated retrieval is not a new observed day; corrected values keep an audit trail."""
    original = archive_snapshot(snapshot(), tmp_path)
    assert archive_snapshot(snapshot(), tmp_path) == original
    archive_snapshot(snapshot("2026-01-03T00:00:00+00:00", 12), tmp_path)
    frame, metadata = accumulated_observations(tmp_path)
    assert metadata["snapshots"] == 2 and len(frame) == 1
    assert frame.iloc[0].price == 12 and frame.iloc[0].date == "2026-01-01"
    readiness = history_readiness(frame).iloc[0]
    assert readiness.distinct_dates == 1 and readiness.history_status == "insufficient_history"
    assert not readiness.forecast_authorized


def test_incomplete_archive_is_explicit_error(tmp_path):
    """A broken archive cannot silently disappear from a reported collection."""
    (tmp_path / "broken.json").write_text("{")
    with pytest.raises(ValueError, match="Invalid archived"):
        accumulated_observations(tmp_path)
    with pytest.raises(ValueError):
        archive_snapshot({**snapshot(), "fetched_at": "2026-01-01"}, tmp_path)


def test_schema_corrupt_and_wrong_identity_caches_are_not_evidence(tmp_path, monkeypatch):
    """Valid JSON alone does not establish a valid cache or product identity."""
    from price_truth import price_api
    monkeypatch.setattr(price_api, "EXTERNAL", tmp_path)
    path = tmp_path / "price_cache/00001234.json"
    for record in [{"fetched_at": datetime.now(UTC).isoformat()},
                   {**snapshot(), "complete_query": True,
                    "observations": [{**snapshot()["observations"][0], "product_code": "99999999"}]}]:
        write_json(path, record)
        with pytest.raises(ValueError, match="No saved"):
            fetch_observations("00001234", offline=True)


@pytest.mark.parametrize(("changes", "message"), [
    ({"observations": None}, "^Snapshot needs an observations list.$"),
    ({"observations": {}}, "^Snapshot needs an observations list.$"),
    ({"source": ""}, "^Snapshot needs an aware timestamp, source and licence.$"),
    ({"license": None}, "^Snapshot needs an aware timestamp, source and licence.$"),
])
def test_snapshot_requirements(changes, message, tmp_path):
    """Snapshots need a list of rows plus provenance metadata."""
    with pytest.raises(ValueError, match=message):
        archive_snapshot({**snapshot(), **changes}, tmp_path)
    assert not list(tmp_path.iterdir())


def test_snapshot_name_is_content_hash_and_existing_file_is_kept(tmp_path):
    """The file name is the SHA-256 of canonical JSON, and an existing file is never rewritten."""
    record = snapshot()
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, allow_nan=False).encode()).hexdigest()
    target = tmp_path / "archive" / f"{digest}.json"
    assert archive_snapshot(record, tmp_path / "archive") == target
    assert json.loads(target.read_text()) == record
    target.write_text('{"sentinel": true}')
    assert archive_snapshot(record, tmp_path / "archive") == target
    assert target.read_text() == '{"sentinel": true}'


def test_snapshot_rejects_non_finite_values(tmp_path):
    """NaN cannot be archived as valid JSON evidence."""
    record = snapshot()
    record["observations"][0]["price"] = float("nan")
    with pytest.raises(ValueError):
        archive_snapshot(record, tmp_path)


def test_empty_archive_metadata(tmp_path):
    """An empty archive reports zero snapshots and no retrieval time."""
    frame, metadata = accumulated_observations(tmp_path)
    assert frame.empty
    assert metadata == {"snapshots": 0, "unique_source_observations": 0, "latest_retrieval": None,
                        "scope": "Latest source revision per observation ID; absent rows are not "
                                 "inferred deletions."}
    assert history_readiness(frame).empty


def test_latest_revision_follows_retrieval_time_not_file_name(tmp_path):
    """Snapshots are ordered by retrieval time; IDs are compared as text within a source."""
    later = snapshot("2026-01-05T00:00:00+00:00", 30)
    earlier = snapshot("2026-01-04T00:00:00+00:00", 20)
    earlier["observations"][0]["id"] = "1"
    other_source = {**snapshot("2026-01-03T00:00:00+00:00", 5), "source": "https://example.com/other"}
    write_json(tmp_path / "a.json", later)
    write_json(tmp_path / "b.json", earlier)
    write_json(tmp_path / "c.json", other_source)
    (tmp_path / "ignored.txt").write_text("not json")
    frame, metadata = accumulated_observations(tmp_path)
    assert metadata["snapshots"] == 3
    assert metadata["unique_source_observations"] == 2
    assert metadata["latest_retrieval"] == "2026-01-05T00:00:00+00:00"
    assert sorted(frame.price.tolist()) == [5, 30]


def test_distinct_ids_in_one_snapshot_are_kept(tmp_path):
    """Different source observation IDs remain separate observations."""
    record = snapshot()
    record["observations"].append({**record["observations"][0], "id": 2, "price": 11})
    archive_snapshot(record, tmp_path)
    frame, metadata = accumulated_observations(tmp_path)
    assert metadata["unique_source_observations"] == 2
    assert frame.price.tolist() == [10, 11]


def test_archived_snapshot_without_rows_is_invalid(tmp_path):
    """A JSON object without an observations list is an explicit archive error."""
    write_json(tmp_path / "x.json", {"fetched_at": "2026-01-01T00:00:00+00:00"})
    with pytest.raises(ValueError, match="^Invalid archived snapshot: x.json$"):
        accumulated_observations(tmp_path)


def test_history_readiness_groups_and_orders():
    """Each barcode/store/currency/basis is reported once, densest first, never authorized."""
    base = snapshot()["observations"][0]
    rows = [{**base, "id": i, "date": f"2026-01-0{i}"} for i in range(1, 4)]
    rows.append({**base, "id": 9, "price_per": None, "location_id": 2})
    readiness = history_readiness(pd.DataFrame(rows))
    assert readiness.columns.tolist() == ["barcode", "store", "currency", "basis", "distinct_dates",
                                          "history_status", "basis_known", "pack_continuity",
                                          "forecast_authorized"]
    assert readiness.distinct_dates.tolist() == [3, 1]
    first, second = readiness.iloc[0], readiness.iloc[1]
    assert (first.barcode, first.store, first.currency, first.basis) == ("00001234", 1, "INR", "UNIT")
    assert bool(first.basis_known) is True
    assert second.basis == "UNKNOWN" and bool(second.basis_known) is False
    assert first.history_status == "insufficient_history"
    assert first.pack_continuity == "Not established by barcode alone"
    assert not readiness.forecast_authorized.any()
