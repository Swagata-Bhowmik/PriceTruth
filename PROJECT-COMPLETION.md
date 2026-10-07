# Price Truth — project status

The single current tracker. Updated **7 October 2026**. The source of truth is the repository https://github.com/Swagata-Bhowmik/PriceTruth, branch `main`. Earlier trackers and plans are kept in [`docs/history/`](docs/history/) and describe earlier states.

## Deadlines

| Date | Deliverable | Status |
|---|---|---|
| August 2026 | Deliverables 1–3: business need, prototype, presentation | Submitted |
| 19 Sep 2026 | Lab Work: code review (40 marks) | Submitted; evidence in [`reports/2026-09-19-lab-submission/`](reports/2026-09-19-lab-submission/) |
| **16 Oct 2026** | **Working Demo (20 marks)** | In preparation; see "Before the demo" below |

## What the application does

Eight pages (see [README](README.md#pages)): Price check (verdict, model range, plain-language SHAP, plus Discount check, Price history & timing and Where to buy tabs, PDF/JSON/CSV export), Unit price, Food & packs, Shrinkflation, My observations, Catalogue, Methods & data, and the built-in User guide.

## Measured state

These figures come from `reports/current/` (generated 7 Oct 2026 by `scripts/review.py` and the audit scripts). Only regenerate them; never edit them by hand.

| Check | Result |
|---|---|
| Tests | 407 passing, no warnings |
| Coverage (package) | 94.51% statements, 86.03% branches |
| Mutation (8 domain modules) | 1,556 / 1,582 killed (98.36%); 26 equivalent survivors in [`docs/MUTATION-SURVIVORS.md`](docs/MUTATION-SURVIVORS.md) |
| Lint / complexity | Ruff clean; every function Radon rank A or B |
| Price model (real listings only) | 4,269 held-out listings: R² 0.959, MAE ₹357, median error 20.8%; Flipkart Electronics weakest (R² 0.01, warned in the app) |
| Discount model (synthetic labels) | Logistic regression, ROC AUC 0.88; precision 23%, recall 48% at threshold 0.17 |
| Browsers (local) | Chrome, Firefox, WebKit flows and PDF download pass; no overflow at 390 / 768 / 1440 px |
| Accessibility | axe-core WCAG A/AA: own issues fixed; remaining findings are inside Streamlit's sidebar navigation |
| Speed (local, 1 user) | Page ≈ 0.9 s, verdict ≈ 1.6 s; first assessment 0.84 s after warm-up |
| Dataset | v1.2, 59 / 59 integrity checks; see [`datasets/final/DATA-CARD.md`](datasets/final/DATA-CARD.md) |
| CI | GitHub Actions *Application checks* (review + Docker build/health) |

## Decisions in force

| Decision | Detail |
|---|---|
| Hosting | Streamlit Community Cloud from this public repo (`app.py`, Python 3.12). The Dockerfile remains for other hosts and is built in CI |
| Accounts | None. Users keep their observations by CSV download and upload |
| Synthetic data | Allowed in clearly labelled layers (histories, discount labels, offers, food histories). Every row carries `provenance`. **The price model trains and evaluates on real listings only.** This replaces the earlier "real data only" rule in the historical plans |
| Presentation | The UI shows synthetic results like real ones. The Methods & data → Dataset tab and all exports state provenance. Reports never present synthetic data as observed fact |
| Shrinkflation | Real cases must be cited; simulated timelines use generic product names |
| Scraping | No scraping of Amazon/Flipkart; only public APIs (Open Food Facts, Open Prices) |

## Open items

### Before the demo (16 Oct)

| # | Item | Owner |
|---|---|---|
| 1 | Deploy on Streamlit Community Cloud (README → Deployment) and set the repository variable `HEALTH_URL` | Swagata (needs her Streamlit/GitHub login) |
| 2 | Hosted checks: browser flows and load test (25 / 50 / 100 users) against the live URL | After 1 |
| 3 | Regenerate `reports/current/` on the final code (CI runs the full review, mutation included) | Before the report and video |
| 4 | Update the Lab Work Word report so its numbers match `reports/current/` | Team |
| 5 | Demo script and a 3–5 minute backup video (route in README → Demo route) | Team |

### After the demo (time- or third-party-bound)

| Item | Earliest | Notes |
|---|---|---|
| 14-day uptime record | 14 days after deployment | `uptime.yml` + `scripts/uptime_report.py` |
| Validated Indian buy-timing forecast | ≈ 16 Nov 2026 | Needs 40 consecutive days of real observations; daily collection began 7 Oct |
| Usability study (5 participants) | When participants are available | Kit in [`docs/USABILITY-STUDY.md`](docs/USABILITY-STUDY.md) |
| Physical phone/tablet, branded Safari/Edge | When devices are available | Viewport emulation already passes |
| Live retailer prices | On approval | Flipkart Affiliate / Amazon Associates API |
| Price model v2 | When an untouched new test set exists | v1 stays with per-category warnings |
| Optional: sale-calendar-aware next-day forecast | Idea | The current forecast rarely beats "same as today" |

## Document map

| Current | Purpose |
|---|---|
| [`README.md`](README.md) | Setup, pages, deployment, automation, demo route |
| `PROJECT-COMPLETION.md` (this file) | Status, decisions, open items |
| [`CLAUDE.md`](CLAUDE.md) | Context for coding agents |
| [`datasets/final/DATA-CARD.md`](datasets/final/DATA-CARD.md), [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md) | Dataset and sources |
| [`reports/current/CODE-REVIEW-REPORT.md`](reports/current/CODE-REVIEW-REPORT.md) + raw evidence | Engineering review |
| [`docs/MUTATION-SURVIVORS.md`](docs/MUTATION-SURVIVORS.md), [`docs/USABILITY-STUDY.md`](docs/USABILITY-STUDY.md), [`docs/USER-GUIDE.html`](docs/USER-GUIDE.html) | Supporting documents |

| Historical | Describes |
|---|---|
| [`docs/history/`](docs/history/README.md) | Earlier trackers, plans and handoffs (19 Sep – 7 Oct) |
| [`reports/2026-09-19-lab-submission/`](reports/2026-09-19-lab-submission/) | Evidence behind the submitted Lab Work report |
