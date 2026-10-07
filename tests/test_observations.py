"""Import validation, daily aggregation and pack-change contracts on labelled test fixtures."""
from datetime import date

import pandas as pd
import pytest

from price_truth import observations
from price_truth.observations import (
    COLUMNS,
    MAX_ROWS,
    daily_series,
    evidence_url,
    pack_changes,
    read_csv,
    validate_observations,
)

TODAY = date(2026, 3, 1)


def row(**changes) -> dict:
    """One test-only quote; example.com links mark it as a fixture, not market evidence."""
    base = {"product_id": "00123", "name": "Test food", "variant": "plain", "store": "shop",
            "currency": "INR", "date": "2026-01-01", "price": 10, "quantity": 100, "unit": "g",
            "source_url": "https://example.com/1"}
    return {**base, **changes}


def frame(*rows: dict) -> pd.DataFrame:
    """Build an import frame with object columns so any test value can be placed."""
    return pd.DataFrame(list(rows) or [row()]).astype(object)


def validate(*rows: dict) -> pd.DataFrame:
    """Validate with a fixed date so future-date boundaries are deterministic."""
    return validate_observations(frame(*rows), today=TODAY)


@pytest.mark.parametrize("url", ["https://example.com/receipt", "  https://example.com/a?b=1  "])
def test_evidence_url_accepts_https_and_strips(url):
    """Accepted links are returned stripped and otherwise unchanged."""
    assert evidence_url(url) == url.strip()


@pytest.mark.parametrize("url", ["http://example.com/a", "https://", "https://u@example.com/a",
                                 "https://:p@example.com/a", "https://example.com/a b",
                                 "https://example.com/\ta", "ftp://example.com", ""])
def test_evidence_url_rejects_unsafe_links(url):
    """Plain HTTP, credentials, missing hosts and embedded whitespace are rejected."""
    with pytest.raises(ValueError, match="^Each source must be an HTTPS link without credentials or spaces.$"):
        evidence_url(url)


def test_valid_import_is_normalized_sorted_and_labelled():
    """Text is stripped, codes are normalized, rows are sorted and labelled unverified."""
    result = validate(row(date="2026-02-01", price="12.5", quantity="100", currency=" inr ",
                          unit=" G ", store=" shop ", source_url=" https://example.com/2 "),
                      row(), row())
    assert result.columns.tolist() == COLUMNS + ["provenance"]
    assert result.index.tolist() == [0, 1]
    assert result.date.tolist() == ["2026-01-01", "2026-02-01"]
    assert result.currency.tolist() == ["INR", "INR"]
    assert result.unit.tolist() == ["g", "g"]
    assert result.store.tolist() == ["shop", "shop"]
    assert result.price.tolist() == [10.0, 12.5]
    assert result.quantity.tolist() == [100.0, 100.0]
    assert result.source_url.tolist() == ["https://example.com/1", "https://example.com/2"]
    assert result.provenance.eq("user_supplied_unverified").all()


def test_sort_uses_identity_before_date():
    """Rows are grouped by identity first, so each pack history stays contiguous."""
    result = validate(row(store="b", date="2026-01-01"), row(store="a", date="2026-02-01"),
                      row(store="a", date="2026-01-15"))
    assert result.store.tolist() == ["a", "a", "b"]
    assert result.date.tolist() == ["2026-01-15", "2026-02-01", "2026-01-01"]


def test_extra_columns_are_dropped_and_input_untouched():
    """Only documented columns are kept, and the caller's frame is not modified."""
    data = frame(row(note="ignored", currency="inr"))
    result = validate_observations(data, today=TODAY)
    assert "note" not in result.columns
    assert data.loc[0, "currency"] == "inr"


def test_missing_columns_message_lists_all_columns():
    """Schema errors name every required column."""
    with pytest.raises(ValueError) as error:
        validate_observations(frame().drop(columns="unit"), today=TODAY)
    assert str(error.value) == "Required columns: " + ", ".join(COLUMNS)


def test_row_bounds():
    """Imports must contain between one and MAX_ROWS rows."""
    message = f"^Supply between 1 and {MAX_ROWS:,} observations.$"
    with pytest.raises(ValueError, match=message):
        validate_observations(pd.DataFrame(columns=COLUMNS), today=TODAY)
    rows = [row(product_id=f"{i:05d}", name=f"Item {i}") for i in range(MAX_ROWS + 1)]
    with pytest.raises(ValueError, match=message):
        validate_observations(pd.DataFrame(rows), today=TODAY)
    assert len(validate_observations(pd.DataFrame(rows[:MAX_ROWS]), today=TODAY)) == MAX_ROWS


@pytest.mark.parametrize("column", ["product_id", "name", "variant", "store", "currency", "unit"])
@pytest.mark.parametrize("value", ["", "   ", None])
def test_required_text_columns(column, value):
    """Blank or missing identity text is rejected with the column named."""
    with pytest.raises(ValueError, match=f"^{column}: supply non-empty text of at most 200 characters.$"):
        validate(row(**{column: value}))


@pytest.mark.parametrize("column", ["product_id", "name", "variant", "store"])
def test_text_length_limit_is_inclusive(column):
    """Exactly 200 characters is accepted; 201 is not."""
    assert validate(row(**{column: "x" * 200}))[column].iloc[0] == "x" * 200
    with pytest.raises(ValueError, match="at most 200 characters"):
        validate(row(**{column: "x" * 201}))


@pytest.mark.parametrize("currency", ["IN", "INRS", "IN1", "€€€"])
def test_currency_must_be_three_letters(currency):
    """Currency codes are three ASCII letters after upper-casing."""
    with pytest.raises(ValueError, match="^Currency must be a three-letter code, for example INR.$"):
        validate(row(currency=currency))


@pytest.mark.parametrize("unit", ["G", "Kg", "ML", "L", "Count"])
def test_units_are_case_insensitive(unit):
    """Supported units are accepted in any case and stored lower-case."""
    assert validate(row(unit=unit)).unit.iloc[0] == unit.lower()


def test_unknown_unit_rejected():
    """Unsupported units are named in the error."""
    with pytest.raises(ValueError, match="^Units must be g, kg, ml, l or count.$"):
        validate(row(unit="box"))


@pytest.mark.parametrize("value", ["2026/01/01", "01-01-2026", "2026-1-01", "2026-01-01x",
                                   "x2026-01-01", "", "2026-01-01 00:00"])
def test_dates_must_be_iso_format(value):
    """Only the strict YYYY-MM-DD form is accepted."""
    with pytest.raises(ValueError, match="^Dates must use YYYY-MM-DD.$"):
        validate(row(date=value))


@pytest.mark.parametrize("value", ["2026-02-30", "2026-13-01", "2026-03-02"])
def test_dates_must_exist_and_not_be_future(value):
    """Impossible and future dates are rejected; today itself is accepted."""
    with pytest.raises(ValueError, match="^Dates must be valid and cannot be in the future.$"):
        validate(row(date=value))
    assert validate(row(date="2026-03-01")).date.iloc[0] == "2026-03-01"


def test_default_today_is_the_current_date():
    """Without an explicit date, today's quotes pass and tomorrow's would not."""
    today = date.today().isoformat()
    assert validate_observations(frame(row(date=today))).date.iloc[0] == today


@pytest.mark.parametrize(("column", "value"), [("price", 0), ("price", -1), ("price", "x"),
                                               ("price", None), ("quantity", "inf"),
                                               ("quantity", 0), ("price", "1e400")])
def test_amounts_must_be_finite_and_positive(column, value):
    """Prices and quantities share one validation error."""
    with pytest.raises(ValueError, match="^Prices and quantities must be finite positive numbers.$"):
        validate(row(**{column: value}))


def test_amount_overflow_is_a_validation_error():
    """Integers too large for a float are reported like any other invalid amount."""
    data = frame()
    data.loc[0, "quantity"] = 10**400
    with pytest.raises(ValueError, match="^Prices and quantities must be finite positive numbers.$"):
        validate_observations(data, today=TODAY)


def test_conflicting_names_for_one_product_id():
    """One ID cannot name two products within an import."""
    with pytest.raises(ValueError, match="^One product ID cannot have conflicting names within an import.$"):
        validate(row(), row(name="Other", date="2026-01-02"))
    assert len(validate(row(), row(product_id="2", name="Other"))) == 2


def test_read_csv_preserves_text_and_validates():
    """CSV text is read as strings, then the full import is validated."""
    payload = frame(row(product_id="007")).to_csv(index=False).encode()
    result = read_csv(payload)
    assert result.product_id.tolist() == ["007"]
    assert result.price.tolist() == [10.0]


def test_read_csv_size_limit_is_inclusive():
    """Exactly MAX_BYTES reaches parsing; one more byte is rejected before parsing."""
    with pytest.raises(ValueError, match="^CSV must be at most 2 MB.$"):
        read_csv(b"x" * (observations.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="^Required columns"):
        read_csv(b"x" * observations.MAX_BYTES)


@pytest.mark.parametrize("payload", [b"", b"\xff\xfe\x00", b'a,b\n"unterminated'])
def test_read_csv_unparseable(payload):
    """Unreadable bytes produce the documented upload message."""
    with pytest.raises(ValueError, match="^Upload a UTF-8 CSV with the documented columns.$"):
        read_csv(payload)


def test_read_csv_reads_all_allowed_rows_and_rejects_more():
    """The row cap allows exactly MAX_ROWS rows and detects one extra."""
    rows = [row(product_id=f"{i:05d}", name=f"Item {i}") for i in range(MAX_ROWS + 1)]
    data = pd.DataFrame(rows)
    assert len(read_csv(data.iloc[:MAX_ROWS].to_csv(index=False).encode())) == MAX_ROWS
    with pytest.raises(ValueError, match="Supply between"):
        read_csv(data.to_csv(index=False).encode())


def test_daily_series_identity_and_median():
    """One identity is required; same-day prices collapse to a median with a count."""
    data = validate(row(), row(date="2026-01-01", price=20, source_url="https://example.com/2"),
                    row(date="2026-01-01", price=60, source_url="https://example.com/3"),
                    row(date="2026-01-03", price=12))
    series = daily_series(data)
    assert series.columns.tolist() == ["date", "price", "observations"]
    assert series.date.tolist() == [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03")]
    assert series.price.tolist() == [20, 12]
    assert series.observations.tolist() == [3, 1]
    for column, value in [("product_id", "x"), ("variant", "x"), ("store", "x"),
                          ("currency", "USD"), ("unit", "kg"), ("quantity", 5.0)]:
        changed = data.copy()
        changed.loc[0, column] = value
        with pytest.raises(ValueError, match="^Select one product, variant, store, currency, unit "
                                             "and pack quantity.$"):
            daily_series(changed)


def history(*rows: dict) -> pd.DataFrame:
    """Validated pack history for pack-change tests."""
    return validate(*rows)


def test_pack_change_requires_confirmation():
    """Continuity must be explicitly confirmed by the uploader."""
    with pytest.raises(ValueError, match="^Confirm these records describe the same product variant "
                                         "over time.$"):
        pack_changes(history(row()))


@pytest.mark.parametrize("column", ["product_id", "variant", "store", "currency"])
def test_pack_change_single_identity(column):
    """Product, variant, store and currency must be unique."""
    data = history(row(), row(date="2026-02-01"))
    data.loc[1, column] = "XYZ"
    with pytest.raises(ValueError, match="^Select one product variant, store and currency.$"):
        pack_changes(data, True)


def test_pack_change_rejects_empty_and_mixed_dimensions():
    """Empty histories and mixed mass/volume units are refused."""
    with pytest.raises(ValueError, match="^Select one product variant"):
        pack_changes(history(row()).iloc[0:0], True)
    with pytest.raises(ValueError, match="^Mass, volume and count observations cannot be mixed.$"):
        pack_changes(history(row(), row(date="2026-02-01", unit="ml")), True)


def test_pack_change_converts_units_and_reports_sources():
    """A 1 kg to 800 g change at the same price is a 20% shrink and 25% unit-price rise."""
    data = history(row(quantity=1, unit="kg", price=100),
                   row(date="2026-02-01", quantity=800, unit="g", price=100,
                       source_url="https://example.com/2"),
                   row(date="2026-03-01", quantity=800, unit="g", price=120,
                       source_url="https://example.com/3"))
    result = pack_changes(data, True)
    assert len(result) == 2
    first, second = result.iloc[0], result.iloc[1]
    assert (first.from_date, first.to_date) == ("2026-01-01", "2026-02-01")
    assert (second.from_date, second.to_date) == ("2026-02-01", "2026-03-01")
    assert first.quantity_reduction_pct == pytest.approx(20)
    assert first.unit_price_increase_pct == pytest.approx(25)
    assert second.quantity_reduction_pct == pytest.approx(0)
    assert second.unit_price_increase_pct == pytest.approx(20)
    assert first.new_unit_price == pytest.approx(12.5)
    assert second.new_unit_price == pytest.approx(15)
    assert first.before_source == "https://example.com/1"
    assert first.after_source == "https://example.com/2"
    assert first.evidence == ("User-supplied; continuity confirmed by uploader, "
                              "not independently verified")


def test_pack_change_converts_the_later_pack_too():
    """An 800 g pack replaced by a 1 kg pack is a 25% size increase, not a shrink."""
    data = history(row(quantity=800, unit="g", price=100),
                   row(date="2026-02-01", quantity=1, unit="kg", price=100))
    result = pack_changes(data, True).iloc[0]
    assert result.quantity_reduction_pct == pytest.approx(-25)
    assert result.unit_price_increase_pct == pytest.approx(-20)


def test_pack_change_same_day_duplicates_collapse():
    """Identical same-day records count once and a single date yields no change rows."""
    data = history(row(), row(source_url="https://example.com/2"))
    assert pack_changes(data, True).empty


def test_pack_change_same_day_conflicts():
    """Different sizes or prices on one date need reconciliation."""
    with pytest.raises(ValueError, match="^Multiple sizes on one date may be pack variants, "
                                         "not a size change.$"):
        pack_changes(history(row(), row(quantity=1, unit="kg")), True)
    with pytest.raises(ValueError, match="^Conflicting same-day prices need reconciliation before "
                                         "pack-change analysis.$"):
        pack_changes(history(row(), row(price=11)), True)
    same_size = history(row(), row(quantity=0.1, unit="kg", source_url="https://example.com/2"))
    assert pack_changes(same_size, True).empty
