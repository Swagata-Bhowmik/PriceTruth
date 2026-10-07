# Price Truth — code review report

| Field | Value |
| --- | --- |
| Module | S3 Lab Work — Group 11 |
| Generated | 2026-09-19T07:35:28.854632+00:00 |
| Team | Swagata Bhowmik B053; Charvi Rathod B049; Yashwi Shah B036 |
| Course | NMIMS MSc Data Science; Dr Yogesh Naik |
| Functional demo | http://localhost:8501 (local server) |
| Reference prototype | https://price-truth.netlify.app/ |
| Environment | macOS-26.5.2-arm64-arm-64bit |
| Python | 3.12.0 |

## 1. Codebase — 10 marks

```text
app.py                  # navigation and cached resources
src/price_truth/
  data.py               # real catalogue cleaning and audit
  model.py              # training, calibration, SHAP
  calculations.py       # unit price, discount, shrink arithmetic
  history.py            # store/currency/date isolation and abstention
  catalogue.py          # search and safe exports
  external.py           # official API clients and dated caches
  ui.py                 # feature screens
  paths.py              # project paths
scripts/                # acquisition, browser checks, this report
tests/                  # domain, data, ML, service and interface checks
datasets/               # original, processed and attributed external data
artifacts/              # trusted fitted model
reports/                # raw and compiled review evidence
```

| Layer | Python files | SLOC |
| --- | --- | --- |
| Data | 1 | 107 |
| ML | 1 | 149 |
| Domain / external services | 4 | 174 |
| Interface | 2 | 279 |
| Infrastructure / scripts | 5 | 308 |
| Tests | 6 | 361 |
| TOTAL | 19 | 1378 |

## 2. Frameworks — 10 marks

| Library | Version | Role / justification |
| --- | --- | --- |
| pandas | 2.3.3 | Tabular ingestion and cleaning |
| numpy | 2.3.5 | Numerical arrays and log transforms |
| scikit-learn | 1.8.0 | Grouped splits, tree candidates and preprocessing; boosting selected by validation error |
| shap | 0.52.0 | Actual Tree SHAP contributions |
| streamlit | 1.57.0 | Functional Python interface and caching |
| plotly | 6.6.0 | Interactive evidence charts |
| requests | 2.33.1 | Bounded official API requests |
| pytest | 9.0.3 | Behavior and integration tests |
| pytest-cov | 7.1.0 | Statement and branch coverage |
| ruff | 0.16.8 | Configured lint rules |
| mutmut | 3.8.0 | Executable mutation testing |
| radon | 6.0.1 | Complexity, maintainability, raw and Halstead metrics |
| playwright | 1.63.0 | Isolated local Chrome verification |

## 3. Code quality — 10 marks

### Ruff

| Rules | Violations | Evidence |
| --- | --- | --- |
| E4/E7/E9/F/I/B/UP | 0 | ruff.json |

Scope: src, app, scripts, tests. This is the configured rule set, not all possible style rules.

### PyTest and coverage

| Test module | Executed cases |
| --- | --- |
| tests.test_app | 11 |
| tests.test_calculations | 43 |
| tests.test_data | 10 |
| tests.test_model | 5 |
| tests.test_search | 5 |
| tests.test_services | 24 |

| Measure | Result |
| --- | --- |
| tests | 98 |
| failures | 0 |
| errors | 0 |
| skipped | 0 |
| time | 14.223 |
| Statement coverage | 462/526 |
| Branch coverage | 74/98 |

| Package file | Covered statements | Statements | Missing branches |
| --- | --- | --- | --- |
| src/price_truth/__init__.py | 0 | 0 | 0 |
| src/price_truth/calculations.py | 35 | 35 | 0 |
| src/price_truth/catalogue.py | 19 | 19 | 0 |
| src/price_truth/data.py | 66 | 82 | 3 |
| src/price_truth/external.py | 56 | 65 | 5 |
| src/price_truth/history.py | 31 | 31 | 0 |
| src/price_truth/model.py | 103 | 104 | 1 |
| src/price_truth/paths.py | 7 | 7 | 0 |
| src/price_truth/ui.py | 145 | 183 | 15 |

Coverage scope: price_truth package; app.py is exercised with Streamlit AppTest but is outside this coverage denominator. Scripts are linted and measured by Radon, not coverage. Test-only boundary fixtures do not enter model training or displayed data.

### Mutmut

| Outcome | Count |
| --- | --- |
| killed | 305 |
| survived | 70 |
| total | 375 |
| no_tests | 0 |
| skipped | 0 |
| suspicious | 0 |
| timeout | 0 |
| check_was_interrupted_by_user | 0 |
| segfault | 0 |

Actual kill rate: 81.33% of 375 generated mutants. Scope: calculations.py, catalogue.py, history.py only. No whole-project mutation claim. All mutant IDs/statuses are in mutmut-results.txt; surviving mutants remain review work.

Mutation testing exposed missing multipack-ranking and history-isolation assertions; strengthened tests check pack counts, barcode, store, currency, unit basis, dates, proof and duplicate status. Error-message and cosmetic mutations can still survive; the count is not adjusted to exclude them.

| Mutant | Change | Observed outcome | Test mechanism / gap |
| --- | --- | --- | --- |
| price_truth.calculations.x_positive__mutmut_1 | Numeric conversion removed | killed | Valid numeric inputs must work |
| price_truth.calculations.x_compare_packs__mutmut_28 | Multipack count omitted | killed | Multipack ranking must use total quantity |
| price_truth.calculations.x_positive__mutmut_8 | Validation message removed | survived | Survivor: exception type is checked, exact wording is not |
| price_truth.history.x_series_for__mutmut_1 | Default unit changed | survived | Survivor: tests and UI pass the unit explicitly; default call remains a test gap |

```diff
# price_truth.calculations.x_positive__mutmut_1: killed
--- src/price_truth/calculations.py
+++ src/price_truth/calculations.py
@@ -1,6 +1,6 @@
 def positive(value: float) -> float:
     """Return a finite positive number or raise a user-facing validation error."""
-    number = float(value)
+    number = None
     if not math.isfinite(number) or number <= 0:
         raise ValueError("Enter a finite value greater than zero.")
     return number
```

```diff
# price_truth.calculations.x_compare_packs__mutmut_28: killed
--- src/price_truth/calculations.py
+++ src/price_truth/calculations.py
@@ -5,7 +5,7 @@
     currencies = {p["currency"].strip().upper() for p in packs}
     if len(currencies) != 1 or "" in currencies:
         raise ValueError("Use the same currency for every pack.")
-    results = [{**p, **unit_price(p["price"], p["quantity"], p["unit"], p.get("packs", 1))}
+    results = [{**p, **unit_price(p["price"], p["quantity"], p["unit"], )}
                for p in packs]
     if len({r["dimension"] for r in results}) != 1:
         raise ValueError("Mass, volume, and item counts cannot be compared together.")
```

```diff
# price_truth.calculations.x_positive__mutmut_8: survived
--- src/price_truth/calculations.py
+++ src/price_truth/calculations.py
@@ -2,5 +2,5 @@
     """Return a finite positive number or raise a user-facing validation error."""
     number = float(value)
     if not math.isfinite(number) or number <= 0:
-        raise ValueError("Enter a finite value greater than zero.")
+        raise ValueError(None)
     return number
```

```diff
# price_truth.history.x_series_for__mutmut_1: survived
--- src/price_truth/history.py
+++ src/price_truth/history.py
@@ -1,5 +1,5 @@
 def series_for(frame: pd.DataFrame, code: str, location_id: int, currency: str,
-               price_per: str = "UNIT") -> pd.DataFrame:
+               price_per: str = "XXUNITXX") -> pd.DataFrame:
     """Filter comparable dated observations and collapse same-day repeats to a median."""
     unit = frame.price_per.fillna("UNKNOWN")
     selected = frame[(frame.product_code == code) & (frame.location_id == location_id)
```

### Radon: cyclomatic complexity

| File | Blocks | Mean CC | Max CC | Worst rank |
| --- | --- | --- | --- | --- |
| src/price_truth/ui.py | 6 | 6.67 | 13 | C |
| src/price_truth/calculations.py | 5 | 4.0 | 8 | B |
| src/price_truth/model.py | 8 | 2.12 | 5 | A |
| src/price_truth/external.py | 4 | 5.75 | 10 | B |
| src/price_truth/data.py | 7 | 3.0 | 9 | B |
| src/price_truth/catalogue.py | 3 | 3.33 | 4 | A |
| src/price_truth/history.py | 3 | 4.0 | 7 | B |
| app.py | 3 | 4.67 | 12 | C |
| scripts/fetch_real_data.py | 2 | 5.5 | 6 | B |
| scripts/review.py | 5 | 9.6 | 40 | E |
| scripts/browser_check.py | 1 | 3.0 | 3 | A |

Production/scripts block mean: 4.66; 47 measured blocks. Report-generation code is included; test metrics remain in raw JSON.

### Radon: maintainability index

| File | MI | Rank |
| --- | --- | --- |
| src/price_truth/ui.py | 25.01 | A |
| scripts/review.py | 34.05 | A |
| src/price_truth/model.py | 34.07 | A |
| src/price_truth/external.py | 38.76 | A |
| src/price_truth/calculations.py | 42.83 | A |
| src/price_truth/data.py | 43.12 | A |
| src/price_truth/history.py | 44.55 | A |
| app.py | 45.59 | A |
| scripts/fetch_real_data.py | 47.48 | A |
| src/price_truth/catalogue.py | 55.75 | A |
| scripts/browser_check.py | 58.84 | A |
| src/price_truth/paths.py | 67.73 | A |
| src/price_truth/__init__.py | 100.0 | A |

Radon's rank A starts above MI 19; it is not a percentage quality score.

### Radon: raw metrics

| Measure | Production + scripts | Tests |
| --- | --- | --- |
| loc | 1219 | 537 |
| lloc | 892 | 408 |
| sloc | 1017 | 361 |
| comments | 4 | 0 |
| multi | 0 | 0 |
| blank | 138 | 117 |

### Radon: Halstead

| Module | Vocabulary | Volume | Difficulty | Effort | Estimated bugs |
| --- | --- | --- | --- | --- | --- |
| src/price_truth/paths.py | 10 | 59.795 | 0.667 | 39.863 | 0.02 |
| src/price_truth/ui.py | 74 | 664.412 | 6.871 | 4565.15 | 0.221 |
| src/price_truth/__init__.py | 0 | 0 | 0 | 0 | 0.0 |
| src/price_truth/calculations.py | 61 | 510.043 | 6.98 | 3559.895 | 0.17 |
| src/price_truth/model.py | 56 | 493.625 | 6.087 | 3004.675 | 0.165 |
| src/price_truth/external.py | 35 | 251.335 | 3.103 | 780.005 | 0.084 |
| src/price_truth/data.py | 57 | 548.292 | 8.267 | 4532.544 | 0.183 |
| src/price_truth/catalogue.py | 17 | 73.574 | 2.5 | 183.936 | 0.025 |
| src/price_truth/history.py | 63 | 543.932 | 6.346 | 3451.879 | 0.181 |

Halstead bug values are formula estimates, not observed defect counts.

## 4. Real-data model evidence

| Measure | Value |
| --- | --- |
| Cleaned real listings | 21267 |
| Held-out test listings | 4269 |
| Selected model | hist_gradient_boosting |
| n | 4269 |
| mae_inr | 356.8183279912241 |
| median_absolute_percentage_error | 20.15700963101238 |
| mean_absolute_log_error | 0.27304886114885685 |
| r2 | 0.9575523210096902 |
| interval_coverage | 0.8976341063480909 |

| Validation candidate | Mean absolute log error |
| --- | --- |
| baseline | 0.279389 |
| random_forest | 0.265184 |
| hist_gradient_boosting | 0.261744 |

| Test platform | Combined log MAE | Separate log MAE | Baseline log MAE |
| --- | --- | --- | --- |
| amazon | 0.292458 | 0.311104 | 0.300071 |
| flipkart | 0.271619 | 0.26827 | 0.306395 |

Model estimates historical observed selling prices, not fraud or authenticity. No verified fraud labels exist. Listed price is a predictor; old/undated data and broad intervals limit current-price interpretation. Combining platforms does not improve every platform metric. See model_evaluation.json and ../docs/DATA-SOURCES.md.

### Auditable code excerpts

```python
def features(frame: pd.DataFrame) -> pd.DataFrame:
    """Use only known listing attributes; never selling price or derived discount."""
    out = frame[CATEGORICAL + ["listed_price", "rating", "rating_count"]].copy()
    out["log_listed_price"] = np.log1p(out.listed_price)
    out["log_rating_count"] = np.log1p(out.rating_count)
    return out[NUMERIC + CATEGORICAL]
```

Feature inputs exclude selling price and derived advertised discount. Preprocessing is fitted after grouped splitting; validation selects the model, calibration sets intervals, test data measures final error.

## 5. NFRs — 10 marks (informal ISO 25010 mapping)

| NFR | Quality category | Target | Measured / status | Evidence |
| --- | --- | --- | --- | --- |
| Performance | Performance efficiency | Page <3s; prediction <2s | First browser 3.0439834580174647s; latest 1.029s. First assess 0.926s; warm p95 0.035s | browser*_check.json; performance.json; first page target missed |
| Scalability | Capacity | 100 concurrent users | Not measured | Sequential benchmark only |
| Usability | Interaction capability | Non-technical use without manual | Functional flows checked; user study not conducted | browser_check.json; test_app.py |
| Security | Security | HTTPS; no PII storage | Local HTTP; deployment HTTPS unverified; raw source contains reviewer fields excluded from processed model data | external.py bounded hosts; catalogue.py safe export; no accounts or quote persistence |
| Reliability | Reliability | 99% evaluation-window uptime | Not measured | Local tests do not establish uptime |
| Portability | Flexibility | Desktop/tablet/mobile | 1440px desktop and 390px mobile emulation; overflow=False; tablet/physical device not tested | PNG screenshots; browser_check.json |
| Maintainability | Maintainability | Modular code | 13 production/script files; CC/MI above | Radon JSON; layer table |
| Availability | Reliability | 24/7 accessible | Local server only; not established | Cloud deployment pending |
| Compatibility | Compatibility | Chrome/Firefox/Safari/Edge | Chrome 153.0.8010.52 tested; other browsers untested | browser_check.json |

## 6. Reproduction and remaining work

```sh
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m ruff check src app.py scripts tests --output-format json
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m pytest --cov=price_truth --cov-branch --cov-report=json:reports/coverage.json --junitxml=reports/pytest.xml
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m radon cc src app.py scripts tests -j
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m radon mi src app.py scripts tests -j
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m radon raw src app.py scripts tests -j
/Users/krishsoni/Documents/price-truth/.venv/bin/python -m radon hal src app.py scripts tests -j
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut run 'price_truth.*'
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut results --all true
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut export-cicd-stats
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut show price_truth.calculations.x_positive__mutmut_1
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut show price_truth.calculations.x_compare_packs__mutmut_28
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut show price_truth.calculations.x_positive__mutmut_8
/Users/krishsoni/Documents/price-truth/.venv/bin/mutmut show price_truth.history.x_series_for__mutmut_1
```

Use `.venv/bin/python scripts/review.py` from the repository root after setup; browser evidence is collected separately with `scripts/browser_check.py` while the app runs. Exact package versions, source hashes, platform and exit codes: review_manifest.json. Timings vary by hardware and warm-cache state.

Remaining: review surviving mutants and higher-complexity modules; visual polish; hosted deployment and HTTPS verification; sustained uptime and 100-user load evidence; other browsers/tablet/physical device; user usability study; final demonstration recording. Real histories presently require abstention from current buying advice. Confirm supplied dataset redistribution rights before publishing raw CSVs.
