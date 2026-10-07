# Mutation testing: surviving mutants

Tool: mutmut 3.8.0, run with `mutmut run` from the repository root (Unix only).
Scope comes from `[tool.mutmut] source_paths` in `pyproject.toml`: `calculations`, `catalogue`,
`history`, `observations`, `forecast`, `offers`, `evidence_store` and `price_api`.

Result on 7 October 2026 (after the code-review fixes): **1556 of 1582 mutants killed (98.4%), 26 survived,
0 untested, 0 timeouts, 0 suspicious.** Before this work the extended scope gave 1453/1543 (94.2%) with 90 survivors.

Every survivor below was reviewed by hand. None changes observable behaviour, so no test can
kill it. Each is equivalent for one of the reasons listed. Check them again after any
change to these lines or after a pandas, numpy or Python upgrade.

## Falsy `None` in place of `False`

Some library parameters only check whether a value is truthy, so `None` has the same effect
as `False`.

| Mutant | Change | Why it is equivalent |
|---|---|---|
| `catalogue.x_search__mutmut_7` | `case=False` to `case=None` | pandas `str.contains` turns on case-insensitive matching whenever `case` is falsy |
| `catalogue.x_search__mutmut_8` | `regex=False` to `regex=None` | pandas uses literal matching whenever `regex` is falsy |
| `catalogue.x_export_csv__mutmut_22` | `index=False` to `index=None` | `to_csv` writes the index only when `index` is truthy. The exact-bytes test would catch an index column |
| `history.x_series_for__mutmut_44` | `as_index=False` to `as_index=None` | `groupby` treats a falsy `as_index` as `False`. Tests confirm `date` stays a column |
| `observations.x_daily_series__mutmut_16` | `as_index=False` to `as_index=None` | Same reason as above |
| `evidence_store.x_archive_snapshot__mutmut_28` | `allow_nan=False` to `allow_nan=None` | `json` checks `if not allow_nan`, so NaN is still rejected (tested) |
| `offers.x_compare_observed_offers__mutmut_68` | `reset_index(drop=True)` to `drop=None` | The extra `index` column this adds is dropped by the final column selection |
| `offers.x_compare_observed_offers__mutmut_74` | `reset_index(drop=True)` to `drop=False` | Same reason as above |

## `zip` strictness on sequences that always match in length

| Mutant | Change | Why it is equivalent |
|---|---|---|
| `observations.x_pack_changes__mutmut_38`, `_41`, `_42` | `strict=True` to `None`, removed, or `False` | Both sequences are columns of the same DataFrame, so they always have the same length |
| `offers.x_require_same_pack__mutmut_9`, `_12`, `_13` | Same change | Same reason as above |
| `observations.x_pack_changes__mutmut_74`, `_77` | `strict=False` to `None` or removed | `False` is already the default. The shorter sequence `ordered[1:]` is meant to end the loop |

## Case changes the program normalises anyway

| Mutant | Change | Why it is equivalent |
|---|---|---|
| `calculations.x_compare_packs__mutmut_8` | currency `.upper()` to `.lower()` | The set is only used to check that every pack has the same currency and that none is blank. Upper and lower case give the same answer |
| `catalogue.x_export_csv__mutmut_29` | `"utf-8-sig"` to `"UTF-8-SIG"` | Python codec names ignore case |
| `observations.x_pack_changes__mutmut_70` | `to_dict("records")` to `"RECORDS"` | pandas lower-cases the `orient` argument |
| `forecast.x__backtest__mutmut_61`, `_62` | `selected != "last_price"` to a misspelt literal | When the baseline is selected, its test error equals the baseline error by definition, so `mae < baseline_mae` is already false. The first condition never decides the outcome |

## Defaults that match the explicit argument for validated input

| Mutant | Change | Why it is equivalent |
|---|---|---|
| `observations.x__clean_dates__mutmut_25` | `strftime("%Y-%m-%d")` to `strftime(None)` | Dates are already checked to match `YYYY-MM-DD` with no time part. pandas' default format for timestamps at midnight is the same ISO date |
| `forecast.x_forecast_next_day__mutmut_11` | `to_numpy(dtype=float)` to `dtype=None` | `price` is already numeric after `pd.to_numeric`. Integer arrays give the same float results because `_predict` casts with `float()` and numpy promotes in median and polyfit |

## Resource bound only

| Mutant | Change | Why it is equivalent |
|---|---|---|
| `observations.x_read_csv__mutmut_9`, `_12`, `_15` | `nrows=MAX_ROWS + 1` to `None`, removed, or `MAX_ROWS + 2` | `nrows` stops parsing early. Any file with more than `MAX_ROWS` rows is still rejected by `validate_observations` (tested), and `MAX_BYTES` already limits the input. Only memory use changes. Lowering the bound (for example `MAX_ROWS - 1`) is caught by tests |

## Not equivalent: killed by new tests

These earlier survivors needed new tests to kill them.

- Exact error message text in calculations, observations, offers, evidence_store and price_api
- `safe_url` rejecting a username or a password on its own
- Exact bytes from `export_csv`
- Exact file names in `load_observations`: a recorder test catches wrongly cased names that macOS's case-insensitive file system would hide
- `series_for` keeping prices below 1
- Message keys from `timing_signal`
- Converting the later pack's units in `pack_changes`
- The forecast choosing the rolling median and requiring a strict improvement over the baseline
- Using the caller's `today` in offers
- Relative-only tolerance for tiny pack sizes
- A single quote
- Integer ranks
- Distinct observation IDs within one snapshot
- `duplicate_of` passing through unchanged
- The cache directory name
