"""Behavior checks for the financial arithmetic used by the interface."""
import math

import pytest

from price_truth.calculations import (
    compare_packs,
    discount_percent,
    positive,
    shrink_change,
    unit_price,
)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_reject_nonpositive_or_nonfinite(value):
    """Invalid user amounts must never reach a division or a model."""
    with pytest.raises(ValueError):
        positive(value)


@pytest.mark.parametrize("value", [.01, 1, 155, 571230])
def test_positive_preserves_amount(value):
    """Validation must not round or modify valid amounts."""
    assert positive(value) == value


def test_discount_from_actual_amazon_listing():
    """The first source record is listed at 1099 and sold for 399."""
    assert discount_percent(1099, 399) == pytest.approx(63.6942675159)
    assert discount_percent(399, 399) == 0


def test_reject_inverted_discount():
    """A reference-price discount cannot have a higher selling price."""
    with pytest.raises(ValueError):
        discount_percent(399, 400)


@pytest.mark.parametrize("listed,selling", [(0, 10), (10, 0), (math.inf, 10), (10, math.nan)])
def test_discount_rejects_invalid_prices(listed, selling):
    """Both price inputs must be validated."""
    with pytest.raises(ValueError):
        discount_percent(listed, selling)


@pytest.mark.parametrize("unit,quantity,expected,basis", [
    ("g", 500, 20, "100 g"), ("kg", .5, 20, "100 g"),
    ("ml", 500, 20, "100 ml"), ("l", .5, 20, "100 ml"), ("count", 5, 20, "item")])
def test_unit_conversions(unit, quantity, expected, basis):
    """Equivalent units must produce the same price per standard quantity."""
    result = unit_price(100, quantity, unit)
    assert result["value"] == pytest.approx(expected)
    assert result["basis"] == basis


def test_multipack_and_dimension():
    """Two 100g packs double the denominator, not the price."""
    assert unit_price(40, 100, "g", 2) == {"dimension": "mass", "value": 20, "basis": "100 g"}
    assert unit_price(40, 100, "ml")["dimension"] == "volume"
    assert unit_price(40, 2, "count")["dimension"] == "count"


@pytest.mark.parametrize("packs", [0, -1, 1.5, True, "2"])
def test_invalid_pack_counts(packs):
    """Only positive integer pack counts are meaningful."""
    with pytest.raises(ValueError):
        unit_price(10, 100, "g", packs)


@pytest.mark.parametrize("price,quantity,unit", [(0, 100, "g"), (10, 0, "g"),
                                                (math.nan, 100, "g"), (10, 100, "oz")])
def test_invalid_units_and_amounts(price, quantity, unit):
    """Invalid input is rejected instead of returning a misleading comparison."""
    with pytest.raises(ValueError):
        unit_price(price, quantity, unit)


def packs():
    """Return isolated user-input fixtures, never part of training data."""
    return [{"name": "A", "price": 25, "quantity": 100, "unit": "g", "currency": "INR"},
            {"name": "B", "price": 40, "quantity": .2, "unit": "kg", "currency": "INR"}]


def test_compare_rank_and_no_mutation():
    """The cheaper normalized option wins without modifying user input."""
    options = packs()
    ranked = compare_packs(options)
    assert [p["name"] for p in ranked] == ["B", "A"]
    assert [p["value"] for p in ranked] == [20, 25]
    assert "value" not in options[0]


def test_currency_normalization():
    """Case and whitespace should not create artificial currency mismatches."""
    options = packs()
    options[0]["currency"] = " inr "
    assert len(compare_packs(options)) == 2


def test_comparison_respects_multipack_count():
    """Mutation testing exposed a gap: ranking must include multipack quantities."""
    options = packs()
    options[0]["packs"] = 3
    ranked = compare_packs(options)
    assert ranked[0]["name"] == "A"
    assert ranked[0]["value"] == pytest.approx(25 / 3)


@pytest.mark.parametrize("currency", ["EUR", "", " "])
def test_reject_mixed_or_missing_currency(currency):
    """No hidden currency conversion is allowed."""
    options = packs()
    options[0]["currency"] = currency
    with pytest.raises(ValueError):
        compare_packs(options)


def test_reject_mixed_dimensions_and_single_pack():
    """Mass and volume cannot be ranked together."""
    options = packs()
    options[0]["unit"] = "ml"
    with pytest.raises(ValueError):
        compare_packs(options)
    with pytest.raises(ValueError):
        compare_packs(options[:1])
    with pytest.raises(ValueError):
        compare_packs([])


def test_reported_vim_shrinkage():
    """Quantity reduction and unit-price increase have different denominators."""
    result = shrink_change(155, 135, 10, 10)
    assert result["quantity_reduction_pct"] == pytest.approx(12.90322580645)
    assert result["unit_price_increase_pct"] == pytest.approx(14.81481481481)


def test_shrinkage_accounts_for_price_change():
    """A larger pack or changed price must not be forced into a shrinkage label."""
    result = shrink_change(100, 200, 10, 30)
    assert result["quantity_reduction_pct"] == -100
    assert result["unit_price_increase_pct"] == pytest.approx(50)


@pytest.mark.parametrize("values", [(0, 100, 10, 10), (100, 0, 10, 10),
                                    (100, 100, 0, 10), (100, 100, 10, 0)])
def test_shrink_rejects_invalid_values(values):
    """All four quantities/prices must be valid."""
    with pytest.raises(ValueError):
        shrink_change(*values)


def test_blank_currencies_cannot_be_compared():
    """Matching missing currencies are not evidence that pack prices are comparable."""
    options = packs()
    for pack in options:
        pack["currency"] = "  "
    with pytest.raises(ValueError, match="currency"):
        compare_packs(options)


@pytest.mark.parametrize(("call", "message"), [
    (lambda: positive(0), "Enter a finite value greater than zero."),
    (lambda: discount_percent(100, 120), "Selling price cannot exceed the listed reference price."),
    (lambda: unit_price(10, 100, "box"), "Supported units: g, kg, ml, l, count."),
    (lambda: unit_price(10, 100, "g", 0), "Pack count must be a positive integer."),
    (lambda: compare_packs([{"price": 1, "quantity": 1, "unit": "g", "currency": "INR"}]),
     "Enter at least two packs of the same product."),
    (lambda: compare_packs([{"price": 1, "quantity": 1, "unit": "g", "currency": "INR"},
                            {"price": 1, "quantity": 1, "unit": "g", "currency": "USD"}]),
     "Use the same currency for every pack."),
    (lambda: compare_packs([{"price": 1, "quantity": 1, "unit": "g", "currency": "INR"},
                            {"price": 1, "quantity": 1, "unit": "ml", "currency": "INR"}]),
     "Mass, volume, and item counts cannot be compared together."),
])
def test_validation_messages_are_exact(call, message):
    """User-facing validation text is part of the interface contract."""
    with pytest.raises(ValueError) as error:
        call()
    assert str(error.value) == message
