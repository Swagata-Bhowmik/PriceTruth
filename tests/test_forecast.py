"""Forecast gates and backtest arithmetic on synthetic, test-only daily series."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from price_truth.forecast import _errors, _predict, forecast_next_day

END = date(2026, 3, 1)


def daily(prices, end: date = END) -> pd.DataFrame:
    """Consecutive daily test series ending on ``end``; not market observations."""
    return pd.DataFrame({"date": pd.date_range(end=end, periods=len(prices)), "price": prices})


def test_last_price_and_rolling_median_windows():
    """Last price uses the final value; the rolling median uses exactly seven values."""
    prices = np.array([1000., 1000., 1, 2, 3, 4, 5, 6, 7])
    assert _predict(prices, "last_price") == 7
    assert _predict(prices, "rolling_median") == 4
    assert _predict(np.array([50., 1, 2, 3, 4, 5, 6]), "rolling_median") == 4
    assert isinstance(_predict(prices, "last_price"), float)


def test_local_trend_uses_fourteen_values_and_floor():
    """The trend fits only the last 14 values and never predicts below 0.01."""
    prices = np.concatenate([[1000., 1000.], np.arange(14.) + 10])
    assert _predict(prices, "local_trend") == pytest.approx(24)
    assert _predict(np.arange(10.) + 5, "local_trend") == pytest.approx(15)
    assert _predict(np.array([100., 50, 1]), "local_trend") == pytest.approx(.01)
    assert _predict(np.array([3., 2, 1]), "local_trend") == pytest.approx(.01)
    assert _predict(np.array([2., 2, 2]), "local_trend") == pytest.approx(2)


def test_errors_are_one_step_absolute_and_expanding():
    """Each error compares one value with a prediction from strictly earlier values."""
    prices = np.array([1., 3, 2, 6, 5])
    assert _errors(prices, 1, 5, "last_price") == [2, 1, 4, 1]
    assert _errors(prices, 3, 4, "last_price") == [4]
    assert _errors(prices, 2, 2, "last_price") == []


def test_trend_is_selected_and_reported():
    """A clean trend selects the local trend, beats the baseline and forecasts tomorrow."""
    result = forecast_next_day(daily(np.arange(60.) + 100), END)
    labels = ["status", "reason", "selected_on_validation", "test_predictions", "forecast_date", "observed_days",
              "age_days"]
    assert {key: result[key] for key in labels} == {
        "status": "evaluated", "reason": "One-step historical backtest; not a guaranteed buying recommendation.",
        "selected_on_validation": "local_trend", "test_predictions": 10, "forecast_date": "2026-03-02",
        "observed_days": 60, "age_days": 0}
    assert result["beats_baseline_on_test"] is True
    numbers = {**result["validation_mae"], "test": result["test_mae"], "baseline": result["baseline_test_mae"],
               "estimate": result["next_day_estimate"]}
    assert numbers == pytest.approx({"last_price": 1, "rolling_median": 4, "local_trend": 0, "test": 0,
                                     "baseline": 1, "estimate": 160}, rel=1e-6, abs=1e-9)


def test_validation_and_test_windows_are_the_last_twenty_days():
    """Days -20..-11 select the method; days -10..-1 score it, and earlier days do neither."""
    prices = np.arange(60.) + 100
    prices[:39] = 100
    result = forecast_next_day(daily(prices), END)
    assert result["validation_mae"]["last_price"] == pytest.approx(1)
    prices[39] = 1000
    shifted = forecast_next_day(daily(prices), END)
    assert shifted["validation_mae"]["last_price"] != pytest.approx(1)
    prices = np.arange(60.) + 100
    prices[49] = 500
    changed = forecast_next_day(daily(prices), END)
    assert changed["validation_mae"]["last_price"] == pytest.approx(
        np.mean(_errors(prices, 40, 50, "last_price")))
    assert changed["baseline_test_mae"] == pytest.approx(np.mean(_errors(prices, 50, 60, "last_price")))


def test_constant_prices_prefer_the_baseline():
    """Ties go to the baseline, which is never reported as an improvement."""
    result = forecast_next_day(daily([100.] * 45), END)
    assert result["status"] == "baseline_preferred"
    assert result["selected_on_validation"] == "last_price"
    assert result["beats_baseline_on_test"] is False
    assert result["next_day_estimate"] is None
    assert result["test_mae"] == result["baseline_test_mae"] == 0


def test_rolling_median_can_win_and_forecasts_with_itself():
    """A repeating 100, 100, 110 pattern favours the median, which then makes the estimate."""
    result = forecast_next_day(daily(np.resize([100., 100., 110.], 60)), END)
    assert result["selected_on_validation"] == "rolling_median"
    assert result["status"] == "evaluated"
    assert result["test_mae"] == pytest.approx(4)
    assert result["baseline_test_mae"] == pytest.approx(7)
    assert result["next_day_estimate"] == pytest.approx(100)


def test_equal_test_error_is_not_an_improvement():
    """A non-baseline method must be strictly better on test data to be promoted."""
    prices = np.full(60, 100.)
    prices[42] = 110
    result = forecast_next_day(daily(prices), END)
    assert result["selected_on_validation"] == "rolling_median"
    assert result["test_mae"] == result["baseline_test_mae"] == 0
    assert result["status"] == "baseline_preferred"
    assert result["next_day_estimate"] is None


def test_selected_method_that_loses_on_test_is_not_promoted():
    """A method chosen on validation must still beat the baseline on the test window."""
    prices = np.arange(60.) + 100
    prices[50:] = prices[49]
    prices[55] = prices[49] + 3
    result = forecast_next_day(daily(prices), END)
    assert result["selected_on_validation"] == "local_trend"
    assert result["test_mae"] > result["baseline_test_mae"]
    assert result["status"] == "baseline_preferred"
    assert result["beats_baseline_on_test"] is False
    assert result["next_day_estimate"] is None


def test_unsorted_and_string_input_is_cleaned():
    """Rows may arrive unsorted and as text; dates are ordered before evaluation."""
    data = daily(np.arange(60.) + 100).astype(str).iloc[::-1]
    result = forecast_next_day(data, END)
    assert result["status"] == "evaluated"
    assert result["next_day_estimate"] == pytest.approx(160)


def test_extra_columns_are_ignored():
    """Only date and price inform the forecast."""
    data = daily(np.arange(60.) + 100).assign(store=None)
    assert forecast_next_day(data, END)["status"] == "evaluated"


@pytest.mark.parametrize("change", [
    {"price": [0.]}, {"price": [-1.]}, {"price": [np.inf]}, {"price": ["abc"]},
    {"price": [np.nan]}, {"date": ["not a date"]}, {"date": [None]},
])
def test_invalid_history(change):
    """Missing, non-numeric, non-positive or infinite values block evaluation."""
    data = daily(np.arange(60.) + 100).astype(object)
    for column, (value,) in change.items():
        data.loc[5, column] = value
    assert forecast_next_day(data, END) == {
        "status": "invalid_history", "reason": "Need unique dates and finite positive prices."}


def test_duplicate_dates_are_invalid():
    """A repeated date is not two days of evidence."""
    data = daily(np.arange(60.) + 100)
    data.loc[5, "date"] = data.loc[6, "date"]
    assert forecast_next_day(data, END)["status"] == "invalid_history"


def test_forty_days_is_the_minimum():
    """Thirty-nine days abstain with a count; forty days are evaluated."""
    assert forecast_next_day(daily(np.arange(39.) + 1), END) == {
        "status": "insufficient_history",
        "reason": "At least 40 consecutive daily observations required.", "observed_days": 39}
    assert forecast_next_day(daily(np.arange(40.) + 1), END)["status"] == "evaluated"


def test_missing_days_are_not_interpolated():
    """A gap blocks evaluation even with enough rows."""
    data = daily(np.arange(61.) + 100).drop(index=10)
    assert forecast_next_day(data, END) == {
        "status": "irregular_history", "reason": "Missing days are not fabricated or interpolated."}


@pytest.mark.parametrize(("offset", "status"), [(-1, "stale_history"), (0, "evaluated"),
                                                (1, "evaluated"), (2, "stale_history")])
def test_last_observation_must_be_today_or_yesterday(offset, status):
    """The final observation may be zero or one day old."""
    result = forecast_next_day(daily(np.arange(60.) + 100), END + timedelta(days=offset))
    assert result["status"] == status
    if status == "stale_history":
        assert result == {"status": status, "reason": "Last observation must be today or yesterday.",
                          "age_days": offset}
    else:
        assert result["age_days"] == offset
        assert result["forecast_date"] == "2026-03-02"


def test_default_today():
    """Without an explicit date, a series ending today is current."""
    assert forecast_next_day(daily(np.arange(60.) + 100, date.today()))["age_days"] == 0
