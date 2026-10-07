# Price Truth

A functional Python web application for explaining observed product prices, looking up food packs, comparing unit prices, and showing sourced price/pack history. Built for Group 11's NMIMS M.Sc. Data Science project.

The active completion record is [PROJECT-COMPLETION.md](PROJECT-COMPLETION.md). September submission evidence is preserved; new checks are in `reports/current/`.

## Run the existing local build

From the project folder:

```bash
.venv/bin/python -m streamlit run app.py
```

Open `http://localhost:8501`. The current workspace already includes the cleaned catalogue, trained model, real API caches, and source evidence, so the demo can run without downloading data again. Live barcode/name search needs internet; use the explicitly labeled saved examples when offline.

## Set up a fresh environment

Python 3.12 is recommended. On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m price_truth.data
.venv/bin/python -m price_truth.model
.venv/bin/python scripts/build_final_dataset.py
.venv/bin/python -m streamlit run app.py
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. Mutmut needs a Unix environment (WSL on Windows). The initial development environment reused preinstalled scientific packages; pinned direct dependencies are in `requirements.txt` and review dependencies in `requirements-dev.txt`.

Keep the user-supplied files at `datasets/amazon/amazon.csv` and `datasets/flipkart/flipkart_com-ecommerce_sample.csv`. Raw files are never overwritten by the pipeline.

Refresh public evidence when needed:

```bash
.venv/bin/python scripts/fetch_real_data.py
```

This performs read-only public API calls and writes attributed snapshots under `datasets/external`. It does not scrape Amazon/Flipkart, create accounts, or upload user data. Price histories remain separate from the training catalogue. The search page saves its own successful queries as offline fallbacks.

## Pages

| Page | What it does |
|---|---|
| Home | Search-first entry, real coverage numbers, links to each tool |
| Price check | Pick an Amazon/Flipkart listing, enter a price, get a verdict (lower / in line / higher than expected), the model's range and a plain-language SHAP explanation; then **Discount check** (30-day reference-price rule + discount-authenticity model), **Price history & timing** (180-day chart with sale events, buy-timing signal, gated forecast, next sale) and **Where to buy** (8 platforms, delivery and fees); PDF/JSON/CSV export |
| Unit price | Compare 2–4 pack options per 100 g, 100 ml or item; best-value verdict and chart |
| Food & packs | Barcode or name lookup (Open Food Facts, live with saved fallback), pack details, dated Open Prices shop history, a long EUR history example; send a pack to Unit price |
| Shrinkflation | 10 cited Indian pack-reduction cases (Vim, Haldiram's, Parle-G, Maggi ×7) and 5 simulated multi-step timelines, with the hidden unit-price increase |
| My observations | Manual or CSV observations kept in the session: price history, gated next-day forecast, cross-store quote ranking, pack-change analysis, CSV export |
| Catalogue | Search and export both historical catalogues |
| Methods & data | Model quality by category, data sources and licences, limits, raw reports |

**Dataset.** Real listings (Amazon, crawled 5 Jan 2023; Flipkart 2015–16) are combined with research-calibrated synthetic layers that no public source provides: daily price histories, discount-authenticity labels and cross-platform offers. Every row carries `provenance` (`real`/`synthetic`); the price model uses real data only. See the [dataset card](datasets/final/DATA-CARD.md) and [data sources](docs/DATA-SOURCES.md).

## Architecture

```text
app.py (st.navigation) → views/*.py → page bodies in ui.py / workspace.py
                                        ├─ present.py   plain-language verdicts, SHAP % effects (pure, tested)
                                        ├─ theme.py     brand CSS, verdict/empty-state components, chart styling
                                        └─ resources.py cached catalogue/model + background warm-up
domain modules: data.py · model.py · calculations.py · catalogue.py · history.py · forecast.py
                observations.py · offers.py · external.py · price_api.py · evidence_store.py · exports.py
```

Pages never compute results themselves; they call the domain modules. Observation uploads and manual entries are validated atomically and held in session memory only.

## Review and tests

```bash
.venv/bin/python scripts/review.py
```

The runner writes Ruff, PyTest/coverage, Radon CC/MI/raw/Halstead, scoped Mutmut, timings and a source-hash manifest to `reports/current/`. Read the [current review](reports/current/CODE-REVIEW-REPORT.md). A step-by-step [user guide with screenshots](docs/USER-GUIDE.html) explains every page and number; it is also built into the app at `/user-guide`. Mutation scope is the domain modules listed under `[tool.mutmut]` in `pyproject.toml` (calculations, catalogue, history, observations, forecast, offers, evidence_store and price_api); it is not a whole-application mutation score. Remaining survivors are justified in [docs/MUTATION-SURVIVORS.md](docs/MUTATION-SURVIVORS.md). The original [submission report](reports/CODE-REVIEW-REPORT.md) and `submission/BASELINE-2026-09-19-SOURCE-EVIDENCE.zip` preserve the earlier version.

Additional checks:

```bash
.venv/bin/python scripts/model_audit.py
.venv/bin/python scripts/data_feasibility.py
.venv/bin/python scripts/browser_current.py
```

The data audit makes bounded public API requests and saves a separate current snapshot. The browser check needs the local app running and Chrome (macOS detection, or `PRICE_TRUTH_CHROME` for another executable); otherwise install Playwright Chromium. `PRICE_TRUTH_URL` can override localhost. Viewport emulation is not physical-device testing.

## Deployment

**Live host: Streamlit Community Cloud** (free, HTTPS), deployed from this public repository's `main` branch with `app.py` as the entry point and Python 3.12. Every push to `main` redeploys.

1. Sign in at https://share.streamlit.io with GitHub and choose **Create app → Deploy a public app from GitHub**.
2. Repository `Swagata-Bhowmik/PriceTruth`, branch `main`, main file `app.py`; under **Advanced settings** pick Python **3.12**.
3. After it starts, set the repository variable `HEALTH_URL` (Settings → Secrets and variables → Actions → Variables) to `https://<app>.streamlit.app/~/+/_stcore/health` to enable the 15-minute uptime probe.

A non-root Dockerfile is also provided and is built and health-checked in CI on every push, for hosts such as Render or Hugging Face Spaces:

```bash
docker build -t price-truth .
docker run --rm -p 8501:8501 price-truth
```

Containers and Community Cloud have ephemeral storage: session observations are lost on restart unless downloaded. Dataset licences: Amazon CC BY-NC-SA 4.0, Flipkart CC BY-SA 4.0, Open Food Facts/Open Prices ODbL — non-commercial use with attribution (shown on the Methods & data page).

## Automation

| Workflow | Schedule | Purpose |
|---|---|---|
| `checks.yml` | every push | Ruff, PyTest + coverage, Radon, Mutmut and source manifest; Docker build + health check |
| `collect-prices.yml` | daily 08:00 IST | Bounded Open Prices INR snapshot, archived only when observations changed; builds the real history forecasts need |
| `uptime.yml` | every 15 min | Probes the deployed health endpoint; `scripts/uptime_report.py` summarises measured uptime |

Hosted checks: `PRICE_TRUTH_URL=https://<app>.streamlit.app/~/+ python scripts/browser_current.py` and `... scripts/load_test.py --users 25 50 100`.

## Demo route

1. Home: search "charging cable" → Price check.
2. Price check: pick a listing, keep or change the price, **Check this price**; read the verdict, range chart and "What moved the estimate"; download the PDF.
3. Food & packs: pick a saved product (or search `Maggi` live), open Pack details, **Compare this pack's value** → Unit price, add prices for 2–3 options.
4. Food & packs → Price history: explain why sparse INR data gives no forecast; Long-history example shows a real EUR series.
5. Shrinkflation: show the hidden unit-price increase and open the cited report.
6. My observations: add a receipt, see the forecast gate (n of 40 days).
7. Methods & data: per-category reliability, licences, and what the app cannot do.

## Remaining external work

Time- or third-party-bound items are tracked in [docs/COMPLETION-PLAN.md](docs/COMPLETION-PLAN.md): a 40-day real history before any Indian forecast can be validated, a 14-day uptime window, retailer API approvals, a usability study with real participants ([kit](docs/USABILITY-STUDY.md)) and physical-device checks.
