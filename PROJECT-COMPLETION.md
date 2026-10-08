# Price Truth — project status

The single current tracker. Updated **8 October 2026**. The source of truth is the repository https://github.com/Swagata-Bhowmik/PriceTruth, branch `main`. Earlier trackers and plans are kept in [`docs/history/`](docs/history/) and describe earlier states.

## Deadlines

| Date | Deliverable | Status |
|---|---|---|
| August 2026 | Deliverables 1–3: business need, prototype, presentation | Submitted |
| 19 Sep 2026 | Lab Work: code review (40 marks) | Submitted; evidence in [`reports/2026-09-19-lab-submission/`](reports/2026-09-19-lab-submission/) |
| **16 Oct 2026** | **Working Demo (20 marks)** | In preparation; see "Before the demo" below |

## What the application does

Eight pages (see [README](README.md#pages)): Price check (verdict, model range, plain-language SHAP, plus Discount check, Price history & timing and Where to buy tabs, PDF/JSON/CSV export), Unit price, Food & packs, Shrinkflation, My observations, Catalogue, Methods & data, and the built-in User guide.

## Measured state

Final evidence: the CI review of commit `0d4ca0e` on Linux (8 October 2026), imported into `reports/current/` after its source hashes were checked against the repository. Regenerate it; never edit it by hand.

| Check | Result |
|---|---|
| Tests | 419 passing, 0 failures |
| Coverage (package) | 95.05% statements (1,997/2,101), 87.21% branches (382/438) |
| Mutation (8 domain modules) | 1,556 / 1,582 killed (98.36%); 26 equivalent survivors in [`docs/MUTATION-SURVIVORS.md`](docs/MUTATION-SURVIVORS.md) |
| Lint / complexity | Ruff 0 violations; Radon: 454 blocks rank A, 74 rank B, none C or worse (application, scripts and tests) |
| Security (Bandit SAST) | 0 high, 0 medium, 0 low over 4,396 lines |
| Price model (real listings only) | 4,269 held-out listings: R² 0.959, MAE ₹357, median error 20.8%; Flipkart Electronics weakest (R² 0.01, warned in the app). A verdict is given for 99.6% of listings (subcategory, or category group as a labelled rough guide) |
| Discount model (simulated labels) | Logistic regression, ROC AUC 0.88; precision 23%, recall 48% at threshold 0.17; shown as the secondary check |
| Browsers (CI) | Chromium, Firefox and WebKit: landing-page search, dashboard, section menu, PDF download, unit comparison, shrinkflation and food flows pass; no JavaScript errors; no overflow at 390 / 768 / 1440 px |
| Accessibility | axe-core WCAG A/AA: no serious issue in the app's own markup (including colour contrast of the pastel theme); the remaining findings are inside Streamlit components (dropdown ARIA attribute, hidden file input) |
| Speed | Assessment with SHAP: 0.34 s first, 0.06 s p95 warm; warm dashboard render ~0.25 s server-side. Load test on the CI runner (server and all browsers on one machine): 10/10 users, median 9.2 s to a full verdict; 25/25 users, 24.6 s |
| Hosted (https://pricetruth.streamlit.app, 8 Oct) | Chrome and WebKit: every flow passes on the live site, no app errors (WebKit's blocked Streamlit Cloud analytics calls are recorded as platform notices); analysed dashboard in 5–9 s for one user. Load test from one laptop against the free tier (1 shared CPU): 10/10 users served, median 22 s to a full verdict; 25/25 served, median 55 s. `reports/current/hosted/`, `load_test_hosted.json` |
| Dataset | v1.2, 59 / 59 integrity checks; see [`datasets/final/DATA-CARD.md`](datasets/final/DATA-CARD.md) |
| CI | *Application checks*: review, Docker build and health, three-browser flows and load test; green |

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
| 1 | ~~Deploy on Streamlit Community Cloud~~ Live at https://pricetruth.streamlit.app (8 Oct); `HEALTH_URL` set and the uptime probe green (run #4, 8 Oct) | Done |
| 2 | ~~Hosted checks~~ Done 8 Oct: Chrome + WebKit flows, 10/25-user load test | Done |
| 3 | ~~Regenerate `reports/current/` on the final code~~ Done 8 Oct (commit `0d4ca0e`) | Done |
| 4 | Self-assessment (rubric) emailed to Prof. Naik | Done 8 Oct |
| 4b | Optional: update the September Lab Work Word report so its numbers match `reports/current/` | Team (file is on the Mac) |
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
