"""Validated discount and unit-price arithmetic, independent of ML and the UI."""
import math

UNITS = {"g": ("mass", 1), "kg": ("mass", 1000),
         "ml": ("volume", 1), "l": ("volume", 1000), "count": ("count", 1)}


def positive(value: float) -> float:
    """Return a finite positive number or raise a user-facing validation error."""
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Enter a finite value greater than zero.")
    return number


def discount_percent(listed: float, selling: float) -> float:
    """Calculate the advertised discount; reject inverted price pairs."""
    listed, selling = positive(listed), positive(selling)
    if selling > listed:
        raise ValueError("Selling price cannot exceed the listed reference price.")
    return 100 * (1 - selling / listed)


def unit_price(price: float, quantity: float, unit: str, packs: int = 1) -> dict:
    """Normalize a pack price to 100 g/ml or one count, without mixing dimensions."""
    price, quantity = positive(price), positive(quantity)
    if unit not in UNITS:
        raise ValueError("Supported units: g, kg, ml, l, count.")
    if isinstance(packs, bool) or not isinstance(packs, int) or packs < 1:
        raise ValueError("Pack count must be a positive integer.")
    dimension, factor = UNITS[unit]
    scale = 1 if dimension == "count" else 100
    return {"dimension": dimension, "value": price * scale / (quantity * factor * packs),
            "basis": {"mass": "100 g", "volume": "100 ml", "count": "item"}[dimension]}


def compare_packs(packs: list[dict]) -> list[dict]:
    """Rank variants of one product, requiring a shared currency and dimension."""
    if len(packs) < 2:
        raise ValueError("Enter at least two packs of the same product.")
    currencies = {p["currency"].strip().upper() for p in packs}
    if len(currencies) != 1 or "" in currencies:
        raise ValueError("Use the same currency for every pack.")
    results = [{**p, **unit_price(p["price"], p["quantity"], p["unit"], p.get("packs", 1))}
               for p in packs]
    if len({r["dimension"] for r in results}) != 1:
        raise ValueError("Mass, volume, and item counts cannot be compared together.")
    return sorted(results, key=lambda r: r["value"])


def shrink_change(old_quantity: float, new_quantity: float,
                  old_price: float, new_price: float) -> dict:
    """Measure quantity change and unit-price change for comparable dated packs."""
    old_quantity, new_quantity = positive(old_quantity), positive(new_quantity)
    old_price, new_price = positive(old_price), positive(new_price)
    return {"quantity_reduction_pct": 100 * (1 - new_quantity / old_quantity),
            "unit_price_increase_pct": 100 * ((new_price / new_quantity) /
                                             (old_price / old_quantity) - 1)}

