"""Controlled fixtures exercise evidence gates; none are production training records."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
import requests
from streamlit.testing.v1 import AppTest

from price_truth import price_api
from price_truth.cache import fresh, read_json, write_json
from price_truth.exports import assessment_pdf
from price_truth.forecast import forecast_next_day
from price_truth.observations import (
    COLUMNS,
    daily_series,
    pack_changes,
    read_csv,
    validate_observations,
)
from price_truth.paths import ROOT


def records():
    """Return explicit test-only quotes with source placeholders."""
    return pd.DataFrame([dict(zip(COLUMNS, row, strict=True)) for row in [
        ["00123", "Test food", "plain", "shop", "INR", "2026-01-01", 10, 100, "g", "https://example.com/1"],
        ["00123", "Test food", "plain", "shop", "INR", "2026-02-01", 10, 80, "g", "https://example.com/2"],
    ]])


def test_csv_preserves_identity_and_labels_evidence():
    """Leading zeros survive import; user uploads do not become verified observations."""
    loaded = read_csv(records().to_csv(index=False).encode())
    assert loaded.product_id.tolist() == ["00123", "00123"]
    assert loaded.provenance.eq("user_supplied_unverified").all()
    assert len(read_csv(pd.concat([records(), records()]).to_csv(index=False).encode())) == 2


@pytest.mark.parametrize(("column", "value"), [
    ("price", -1), ("price", "inf"), ("quantity", "nan"), ("currency", "R"),
    ("unit", "box"), ("variant", ""), ("date", "2026-02-31"),
    ("date", "2999-01-01"), ("date", "2026-01-01T00:00:00"),
    ("source_url", "javascript:alert(1)"), ("source_url", "https://user:pass@example.com"),
])
def test_import_rejects_entire_invalid_batch(column, value):
    """A single invalid row prevents partial ingestion."""
    frame = records().astype(object)
    frame.loc[1, column] = value
    with pytest.raises(ValueError):
        validate_observations(frame)


def test_import_bounds_and_schema():
    """Oversized, malformed and incomplete uploads fail predictably."""
    for content in [b"x"*2_000_001, b"bad\n1", b"", b"\xff\xfe"]:
        with pytest.raises(ValueError):
            read_csv(content)


def test_pack_change_needs_confirmation_and_identity():
    """Same-price shrinkage increases unit cost; unrelated store histories cannot combine."""
    frame = validate_observations(records())
    with pytest.raises(ValueError):
        pack_changes(frame)
    result = pack_changes(frame, True).iloc[0]
    assert result.quantity_reduction_pct == pytest.approx(20)
    assert result.unit_price_increase_pct == pytest.approx(25)
    frame.loc[1, "store"] = "other"
    with pytest.raises(ValueError):
        pack_changes(frame, True)


def test_daily_series_requires_same_pack_and_aggregates_dates():
    """Different pack sizes must not become apparent price movements."""
    frame = validate_observations(records())
    with pytest.raises(ValueError):
        daily_series(frame)
    frame["quantity"] = 100
    frame.loc[1, "date"] = frame.loc[0, "date"]
    frame.loc[1, "price"] = 20
    series = daily_series(frame)
    assert series.price.tolist() == [15]
    assert series.observations.tolist() == [2]


def trend():
    """Synthetic daily trend solely for chronological forecast contract tests."""
    return pd.DataFrame({"date": pd.date_range(end=date.today(), periods=60),
                         "price": np.arange(60)+100.})


def test_forecast_chronological_holdout_and_future_gate():
    """Predictable trend wins honestly; changing final test values cannot change selection."""
    data = trend()
    first = forecast_next_day(data)
    assert first["test_predictions"] == 10
    assert first["selected_on_validation"] == "local_trend"
    assert first["next_day_estimate"] == pytest.approx(160)
    assert first["forecast_date"] == (date.today()+timedelta(days=1)).isoformat()
    changed = data.copy()
    changed.loc[50:, "price"] *= 5
    assert forecast_next_day(changed)["validation_mae"] == first["validation_mae"]
    assert forecast_next_day(data, date.today()-timedelta(days=1))["status"] == "stale_history"


def test_forecast_abstains_for_constant_sparse_stale_and_bad_history():
    """No forecast is promoted when baselines suffice or history cannot support it."""
    data = trend()
    assert forecast_next_day(data.iloc[:5])["status"] == "insufficient_history"
    assert forecast_next_day(data.drop(index=10))["status"] == "irregular_history"
    assert forecast_next_day(data, date.today()+timedelta(days=10))["status"] == "stale_history"
    data["price"] = 100.
    result = forecast_next_day(data)
    assert result["status"] == "baseline_preferred" and result["next_day_estimate"] is None
    data.loc[0, "price"] = np.inf
    assert forecast_next_day(data)["status"] == "invalid_history"


def test_price_api_filters_identity_and_contributor_fields(monkeypatch, tmp_path):
    """A live result retains no contributor PII; repeated reads use the bounded cache."""
    monkeypatch.setattr(price_api, "EXTERNAL", tmp_path)
    item = {"id": 1, "product_code": "00001234", "price": 10, "currency": "INR",
            "date": "2026-01-01", "owner": "secret", "proof": {"owner": "private"}}
    monkeypatch.setattr(price_api, "get_json", lambda *a: {"items": [item, {**item, "product_code": "99999999"}], "total": 2, "pages": 2})
    result = price_api.fetch_observations("00001234")
    assert len(result["observations"]) == 1 and not result["complete_query"]
    assert "owner" not in result["observations"][0]
    def failed(*args):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(price_api, "get_json", failed)
    assert price_api.fetch_observations("00001234")["mode"] == "cached"
    with pytest.raises(ValueError):
        price_api.fetch_observations("11111111")
    with pytest.raises(ValueError):
        price_api.fetch_observations("../private")


def observations_app():
    """Open the observations page through the real navigation."""
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
    app.session_state["food_offline"] = True  # no live API calls from tests
    return app.run().switch_page("views/observations.py")


def test_observations_and_food_pages_render_empty_states():
    """Every evidence path renders before any user data exists."""
    app = observations_app().run()
    assert not app.exception and any("Upload real" in i.value for i in app.info)
    app.switch_page("views/food.py").run()
    assert not app.exception


def test_cache_corruption_is_a_miss_and_write_replaces(tmp_path):
    """Interrupted/manual cache corruption cannot masquerade as valid evidence."""
    path = tmp_path / "cache.json"
    path.write_text("{unfinished")
    assert read_json(path) is None
    assert not fresh({"fetched_at": "2026-10-01T10:00:00"})
    write_json(path, {"x": 1})
    assert read_json(path) == {"x": 1}


def test_pdf_export_is_generated_in_memory():
    """A price assessment can be exported without persisting a quote on the server."""
    payload = assessment_pdf({"key": "test:001", "name": "A & B <pack>", "platform": "test"},
                             {"claimed_discount_pct": 20, "estimate": 10, "lower": 5, "upper": 15,
                              "status": "within_model_range", "support": 30, "seen_in_training": False}, 8, 10)
    assert payload.startswith(b"%PDF-") and len(payload) > 1000


def test_manual_observation_validation_and_clear():
    """Manual evidence persists within the session, and explicit deletion removes it."""
    app = observations_app().run()
    for field, value in [("product_id", "00123"), ("name", "Test food"), ("variant", "plain"), ("store", "shop")]:
        app.text_input(key=f"manual_{field}").set_value(value)
    next(i for i in app.text_input if i.label == "HTTPS source / evidence link").set_value("https://example.com/receipt")
    next(i for i in app.number_input if i.label == "Total price paid").set_value(10.)
    next(i for i in app.number_input if i.label == "Total quantity purchased").set_value(100.)
    next(i for i in app.button if i.label == "Add to my session observations").click().run()
    assert not app.exception
    assert app.session_state["observations"].iloc[0].product_id == "00123"
    assert not app.json  # results are explained in words and tables, never raw JSON
    assert any("Not enough history yet" in str(h.proto.body) for h in app.get("html"))
    next(i for i in app.button if i.label == "Clear session observations").click().run()
    assert not app.exception and any("Upload real" in i.value for i in app.info)


def test_pack_changes_rejects_ambiguous_same_day_evidence():
    """Equal numeric quantities in different units must not conceal conflicting packs."""
    data = records()
    data.loc[1, "date"] = data.loc[0, "date"]
    data.loc[1, "quantity"] = 100
    data.loc[1, "unit"] = "kg"
    with pytest.raises(ValueError, match="Multiple sizes"):
        pack_changes(validate_observations(data), True)
    data.loc[1, "unit"] = "g"
    data.loc[1, "price"] = 20
    with pytest.raises(ValueError, match="Conflicting same-day"):
        pack_changes(validate_observations(data), True)


def test_workspace_quote_comparison_uses_confirmed_session_evidence():
    """The new cross-store path reaches real ranking and retains its evidence label."""
    app = observations_app()
    row = records().iloc[0].to_dict()
    row["date"] = date.today().isoformat()
    data = pd.DataFrame([row, {**row, "store": "second shop", "price": 8}])
    app.session_state["observations"] = validate_observations(data)
    app.run()
    app.checkbox(key="offers_confirmed").check()
    next(i for i in app.button if i.label == "Compare sourced store quotes").click().run()
    assert not app.exception
    comparison = next(i.value for i in app.dataframe if "price_rank" in i.value.columns)
    assert comparison.iloc[0].store == "second shop" and comparison.iloc[0].price == 8
