# Price Truth

Price Truth helps Indian online shoppers judge a price before they buy. Pick a product, enter the price you see, and one scrolling dashboard tells you:

- whether the price is fair for that product;
- whether the discount is genuine;
- how the price has moved and whether a sale is coming;
- where it is cheapest, delivery included;
- which pack size is better value, and whether packs have shrunk.

It is the NMIMS M.Sc. Data Science (Semester 3) Group 11 project.

**Live app: https://pricetruth.streamlit.app**

- **Status, decisions and open items:** [PROJECT-COMPLETION.md](PROJECT-COMPLETION.md).
- **How it is built, and why each framework was chosen:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **How to use it:** the [user guide](docs/USER-GUIDE.html), also built into the app at `/user-guide`.

## Run it

```bash
.venv/bin/python -m streamlit run app.py          # macOS/Linux
```

```bash
.venv\Scripts\python.exe -m streamlit run app.py  # Windows
```

Open `http://localhost:8501`. The repository already contains the cleaned catalogue, the trained models, the simulated dataset layers and saved API responses, so the app runs without downloading data. Live food search needs internet; switch on *Saved responses only* to work offline.

## Set up a fresh environment

Python 3.12:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock -r requirements-dev.txt
.venv/bin/python -m streamlit run app.py
```

On Windows use `.venv\Scripts\python.exe` and install with `-r requirements-dev.txt` (the lock file is resolved for Linux).

- `requirements.txt` pins the nine direct runtime dependencies.
- `requirements.lock` pins every package for Linux builds (Docker, CI).
- `requirements-dev.txt` adds the review tools.

Rebuild data and models only when the data changes:

```bash
.venv/bin/python -m price_truth.data               # raw CSVs → datasets/processed/catalogue.csv
.venv/bin/python -m price_truth.model              # price model (real listings only)
.venv/bin/python scripts/build_final_dataset.py    # simulated layers + discount model → datasets/final/
```

The raw files `datasets/amazon/amazon.csv` and `datasets/flipkart/flipkart_com-ecommerce_sample.csv` are never modified; tests check their SHA-256.

## What is in the app

| Page | What it does |
|---|---|
| **Home** | Landing page: what Price Truth does, real coverage figures (animated counters), the two problems it exposes, a feature card per dashboard section, and a product search that opens the dashboard |
| **Dashboard** | You choose Platform → Category → Subcategory → Product and enter the listed MRP and the price you see. Six headline cards show the price verdict, fair price estimate, advertised discount, real saving, inflation risk and best place to buy; hovering a card explains how its figure is produced. The cards below fill the screen width, and a sticky section menu scrolls to: **Fair price** (model range and SHAP explanation), **Discount check** (30-day reference-price rule and classifier risk dial), **Price history** (180-day chart with sale events, buy-timing signal, sale calendar, gated forecast), **Where to buy** (8 platforms, delivery and fees), **Pack value** (unit-price comparison), **Shrinkflation** (10 cited Indian cases and 5 simulated timelines) and **Export** (PDF, JSON, CSV) |
| Food & packs | Barcode or name lookup in Open Food Facts (live, with a saved fallback), dated Open Prices shop history and a long real history example; sends a pack size to the dashboard's Pack value section |
| My observations | Prices you record by hand or import from CSV (session only): price history, gated forecast, store comparison, pack-size changes, CSV export |
| Catalogue | Search and export both historical catalogues |
| Methods & data | Model accuracy by category, which data is real and which is simulated, sources and licences, limits, raw reports |
| User guide | The illustrated guide, with a download |

**Data.** Real listings (Amazon crawled 5 January 2023; Flipkart 2015–16) are combined with research-calibrated simulated layers that no public source provides: daily price histories, discount labels and cross-platform offers. Every row carries `provenance` (`real` or `synthetic`), and **the price model trains and evaluates on real listings only**. See the [dataset card](datasets/final/DATA-CARD.md) and [data sources](docs/DATA-SOURCES.md).

## Architecture

```text
app.py (st.navigation, top menu, JSON logging, motion layer) → views/*.py (one line per page)
   ├─ landing.py     the home page
   ├─ dashboard.py   the product dashboard (layout only)
   ├─ ui.py, workspace.py, market_ui.py   detail pages and shared panels
   ├─ present.py     plain-language verdicts, headline cards, SHAP % effects (pure, tested)
   ├─ theme.py       design system: pastel tokens, CSS, cursor/scroll motion, cards, tooltips, chart template
   └─ resources.py   cached catalogue and models, background warm-up
domain:      model.py · authenticity.py · synthetic.py · calculations.py · catalogue.py · history.py
             forecast.py · observations.py · offers.py
integration: data.py · external.py · price_api.py · evidence_store.py · cache.py · exports.py · logs.py
```

Pages never compute results; they call the domain modules. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains the data flow, module boundaries, data design, the trade-offs behind each framework, and how each non-functional requirement is met and measured.

## Quality checks

```bash
.venv/bin/python -m pytest -q                         # tests (UI tests run offline)
.venv/bin/ruff check .                                # lint
.venv/bin/radon cc -s -n C src scripts app.py views   # prints nothing when every function is rank A/B
.venv/bin/python scripts/review.py                    # full review → reports/current/ (Linux/WSL; includes mutmut)
```

`scripts/review.py` runs Ruff, PyTest with statement and branch coverage, Radon (CC, MI, raw, Halstead), Bandit security scanning (fails on any medium or high finding), mutation testing of the eight domain modules and a latency benchmark. It writes the results and a source-hash manifest to `reports/current/` and renders [the current review](reports/current/CODE-REVIEW-REPORT.md). Surviving mutants are justified in [docs/MUTATION-SURVIVORS.md](docs/MUTATION-SURVIVORS.md). CI runs the same review on every push.

These need a running app (`PRICE_TRUTH_URL` selects it):

```bash
.venv/bin/python scripts/browser_current.py --browser chrome   # also firefox, webkit
.venv/bin/python scripts/load_test.py --users 25 50 100        # concurrent real browsers
.venv/bin/python scripts/build_user_guide.py                   # rebuild docs/USER-GUIDE.html
```

The September Lab Work evidence is kept in [reports/2026-09-19-lab-submission/](reports/2026-09-19-lab-submission/); superseded documents are in [docs/history/](docs/history/README.md).

## Deployment

**Host: Streamlit Community Cloud** (free, HTTPS) at **https://pricetruth.streamlit.app**, deployed from this repository's `main` branch with `app.py` and Python 3.12. Every push redeploys. `app.py` imports the package from `src/` because Community Cloud installs `requirements.txt` but not the package itself.

1. Sign in at https://share.streamlit.io with GitHub → **Create app → Deploy a public app from GitHub**.
2. Repository `Swagata-Bhowmik/PriceTruth`, branch `main`, main file `app.py`; **Advanced settings** → Python **3.12**.
3. Set the repository variable `HEALTH_URL` (Settings → Secrets and variables → Actions → Variables) to `https://<app>.streamlit.app/~/+/_stcore/health` to start the 15-minute uptime probe.

For other hosts (Render, Hugging Face Spaces), use the non-root Docker image, which CI builds and health-checks on every push:

```bash
docker build -t price-truth .
docker run --rm -p 8501:8501 price-truth
```

Storage is ephemeral: session observations are lost on restart unless downloaded. Licences: Amazon CC BY-NC-SA 4.0, Flipkart CC BY-SA 4.0, Open Food Facts / Open Prices ODbL. Use is non-commercial, with attribution (shown on Methods & data).

## Automation

| Workflow | When | What |
|---|---|---|
| `checks.yml` | every push | Full review (Ruff, PyTest + coverage, Radon, Bandit, Mutmut, manifest); Docker build and health check |
| `collect-prices.yml` | daily 08:00 IST | Bounded Open Prices INR snapshot, archived only when observations change |
| `uptime.yml` | every 15 min | Probes the deployed health endpoint; `scripts/uptime_report.py` summarises measured uptime |

## Demo route

1. **Home → Dashboard:** search "cable" on the home page, or open the dashboard and keep the default (Amazon › Electronics, the most-rated HDMI cable). Change *Price you see* and watch every card update; hover a card for its explanation.
2. **Fair price:** the verdict, where your price sits in the expected range, and the SHAP factors behind the estimate.
3. **Discount check:** the 30-day rule against the classifier's risk dial.
4. **Price history:** hover over the 180-day chart; the sale calendar; why the forecast declines.
5. **Where to buy:** total cost by platform.
6. **Pack value:** 400 g for ₹45 against 1 kg for ₹105. Then **Shrinkflation:** a cited case and the hidden price rise.
7. **Export:** download the PDF report.
8. **Methods & data:** accuracy by category, real vs simulated data, licences and limits.
