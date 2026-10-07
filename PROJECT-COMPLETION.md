# Price Truth — completion tracker

Updated: 7 October 2026. The day plan and remaining gates are in [docs/COMPLETION-PLAN.md](docs/COMPLETION-PLAN.md). Current evidence is under `reports/current/` and was regenerated on the final code today. Sections below the line are the 6 October record, kept for history; their numbers are superseded.

## 7 October 2026 status

| Area | Status | Evidence |
|---|---|---|
| Interface | Redesigned: grouped navigation, branded theme, verdict cards, readable SHAP (% effects), empty states, mobile layout | `views/`, `theme.py`, `present.py`; screenshots in `reports/current/` |
| Tests | 358 passing, no warnings | `reports/current/pytest.xml` |
| Coverage | 92.68% statements, 85.33% branches (package incl. UI) | `reports/current/coverage.json` |
| Mutation | 1,517/1,543 killed (98.3%) across 8 domain modules; 26 equivalent survivors justified | `docs/MUTATION-SURVIVORS.md` |
| Complexity | All application functions Radon rank A/B | `reports/current/radon-cc.json` |
| Performance | First assessment 0.88 s (was 9.3 s) after background warm-up; single browser user: page 0.9 s, verdict 1.5 s | `performance.json`, `load_test_local.json` |
| Browsers | Chrome, Firefox, WebKit: all flows incl. PDF download pass, no JS errors, no overflow at 390/768/1440 px | `browser_check.json` (+ `firefox/`, `webkit/`) |
| Accessibility | axe-core WCAG A/AA: own contrast issue fixed; remaining findings are inside Streamlit's sidebar navigation (list markup, `aria-expanded`) | `browser_check.json` |
| CI | GitHub Actions: review + Docker build/health check green | github.com/Swagata-Bhowmik/PriceTruth/actions |
| Deployment | Streamlit Community Cloud from public repo (owner completes the 3-click deploy) | README → Deployment |
| Data collection | Daily Open Prices INR workflow running; archives only changed observations | `collect-prices.yml` |
| Uptime | 15-minute probe workflow; activates when `HEALTH_URL` is set | `uptime.yml`, `scripts/uptime_report.py` |

### Dataset finalisation (7 Oct, afternoon)

- Real fields recovered: Amazon crawl date (5 Jan 2023) from link timestamps, Amazon brand from titles, Flipkart zero rating counts. Price model retrained on the corrected real data: R² 0.962, MAE ₹354 on the same 4,269 held-out listings.
- Research-calibrated synthetic layers added with `provenance`: daily price histories, discount labels (EU Omnibus 30-day reference rule adapted to MRP listings), offers on 8 platforms, food shop histories; 8 newly researched real shrinkflation cases plus 5 generic simulated timelines. See `datasets/final/DATA-CARD.md`.
- New discount-authenticity classifier: ROC AUC 0.88 on unseen products (synthetic labels).
- Price check now has Discount check, Price history & timing, and Where to buy tabs.

### Dataset v1.1 (7 Oct, evening)

- 15 category groups; "Other" 4,901 → 60 listings (source-root mapping plus whole-word title rules for 320 malformed rows).
- Synthetic anchors inflation-adjusted with MoSPI CPI (general monthly index plus category sub-groups): Flipkart ×1.48–1.57, Amazon ×1.09.
- Price model retrained: R² 0.959, MAE ₹357; no category has negative R² any more.

### Still open (cannot be completed in one day)
- Validated Indian buy-timing forecast: needs 40 consecutive days of real observations (collection started 7 Oct).
- 14-day measured uptime window (starts at deployment).
- Live retailer offers: depends on Flipkart Affiliate / Amazon API approval.
- Usability study with five real participants: kit in `docs/USABILITY-STUDY.md`.
- Physical phone/tablet and branded Safari/Edge checks.
- Model v2: needs an untouched new test set; v1 stays with per-category reliability warnings.

---


## Objective and decisions

Complete the connected functional application across price assessment, pack lookup, unit comparison, price history/timing and shrink evidence. Retain Python/Streamlit and prepare Claude for visual polish and subsequent deployment. Both real Amazon and Flipkart datasets remain in use. The trained model is preserved rather than retrained against its frozen test results.

Synthetic fixtures are permitted for tests and stress scenarios only. They do not enter production observations, real-data evaluation, retailer offers or fraud ground truth. An insufficient-evidence result is preferable to fabricated prices. No paid accounts, unauthorized retailer scraping or automatic unrelated-product matching were introduced.

**Overall status: substantially expanded functional local application; full production completion is not yet established.** The external acceptance gates below remain open.

## Work plan and acceptance checks

| Workstream | Status | Delivered / acceptance evidence |
|---|---|---|
| Preserve baseline | Complete | `submission/BASELINE-2026-09-19-SOURCE-EVIDENCE.zip`; original reports unchanged |
| Data/API feasibility | Complete for current public source | Bounded INR refresh, 407 records / 381 barcodes; normalized snapshot with contributor details excluded; cache and provenance labels |
| Connected workspace | Implemented, tested locally | One selected listing drives assessment/export; one barcode drives pack/history; structured pack quantity transfers to comparison |
| Observation ingestion | Implemented, tested | Manual entry and CSV; strict identity/date/quantity/currency/source validation; atomic import; session clear and CSV export |
| Price history and timing | Implemented; real forecast acceptance open | Exact identity and pack filtering; chronology-safe validation/test; reject sparse/stale/irregular data; baseline must be beaten |
| Pack/shrink analysis | Implemented, tested | Explicit same-variant confirmation; normalized quantities; source links; reject ambiguous same-day evidence |
| Portable assessment | Implemented | JSON plus PDF with selected identity, quoted prices, model range and limitations |
| Engineering quality | Current evidence generated | 122 tests; configured Ruff; CC/MI/raw/Halstead; scoped mutation run; source hashes; see current review |
| Model diagnostics | Complete for frozen test split | 4,269 held-out rows; subgroup metrics and controlled reference-price sensitivity recorded |
| Browser verification | Local Chrome verification | Three viewport checks and real PDF download; exact latest result in `reports/current/browser_check.json` |
| Deployment preparation | Configuration supplied; build unverified | Non-root Dockerfile and health check; Docker unavailable locally; no public deployment performed |
| Claude handoff | Updated | `docs/CLAUDE-UI-HANDOFF.md` describes implemented behavior and prohibits invented results |

## What the current data supports

- 21,267 cleaned real marketplace listings: 1,347 Amazon and 19,920 Flipkart. These are historical snapshots, not live offers.
- Frozen held-out price regression: MAE INR 356.82; median absolute percentage error 20.16%; R² 0.95755. High aggregate R² does not establish uniform category quality.
- Subgroup diagnostics reveal negative R² for Flipkart Electronics and Personal care. These are observed weaknesses, not new training targets to tune against the frozen test set. A future model revision needs fresh validation/test evidence.
- A controlled +25% reference-price perturbation changes predictions by median +22.16% (90th percentile +46.74%). This is model sensitivity, not a market observation or causal result. The model is unsuitable as an independent fraud detector.
- Current INR Open Prices audit: 407 observations, 381 barcodes, 282 eligible shop observations. The largest barcode/store/currency/basis group spans only two distinct dates; zero reach 40. Top groups also lack a recorded price basis. No current Indian forecast has been validated.
- Forecast engine: at least 40 consecutive recent daily observations; method selected using ten chronological validation predictions, then evaluated on ten later predictions against persistence. Synthetic trend tests verify code behavior only. Pack continuity must be established independently.

## Review scope and interpretation

`reports/current/CODE-REVIEW-REPORT.md` is generated from actual tools. Raw JSON/XML/logs and `review_manifest.json` bind measurements to current source. `runtime_inventory.json` additionally hashes data, artifacts and runtime configuration. Current measurements: 122 passing tests; zero configured Ruff violations; 787/927 package statements covered (84.90%); 158/216 branches covered (73.15%); 307/375 scoped mutations killed (81.87%), with 68 survivors. Coverage is lower than the smaller September package because new paths expand its denominator. Mutation testing remains limited to calculations, catalogue and history. It is not a whole-product score; surviving mutations remain listed.

The former monolithic `scripts/review.py` main function had CC 40/E. It is now a wrapper around separated stages in `scripts/review_current.py`; consult the current Radon table for each function. Other complex UI/data functions are still reported rather than hidden.

Package coverage excludes scripts and app.py from its denominator. Local sequential SHAP/model timings are not concurrent load results. Cold font-cache creation caused a roughly 9.8-second assessment in an earlier run; warm timings must not be advertised as cold-start guarantees. CPU-detection and sparse-feature warnings remain visible in raw logs.

## Remaining acceptance gates, in order

1. **Suitable real data:** obtain licensed dated observations with exact product/variant/pack/store/currency identity. Collect at least 40 consecutive recent daily observations per forecast target, then validate prospectively. Existing manual/CSV ingestion is ready. Synthetic records cannot close this gate.
2. **Current retailer comparison:** obtain approved retailer/partner feeds and stable exact-product identifiers. Historical Amazon/Flipkart listings and food barcodes cannot be silently matched. Until then, do not advertise live cross-retailer best-price results.
3. **Model improvement:** address weak categories and reference-price dependence using new representative data, new validation and an untouched test set. No fraud/authenticity score is supported without verified labels.
4. **Deployment:** choose the eventual host, verify publication rights, build/test the supplied container, configure HTTPS and required persistence, then test the deployed service. Claude styling/deployment follows the functional handoff. The existing Netlify prototype has not been replaced.
5. **Operational evidence:** measure target-user concurrency, uptime over an actual observation window, user usability/accessibility and additional browsers/physical devices. No invented NFR percentages.
6. **Release review:** after styling/deployment changes, regenerate all current review and browser evidence and update submission documentation for that exact version. September Word/PDF reports are historical and were not rewritten in this pass.

## Reproduction

```bash
.venv/bin/python -m streamlit run app.py
.venv/bin/python scripts/review.py
.venv/bin/python scripts/model_audit.py
.venv/bin/python scripts/data_feasibility.py
.venv/bin/python scripts/browser_current.py
```

The browser command needs the running app and Chrome/Playwright Chromium. The data audit needs network access. User observations remain in server session memory; download CSV to retain them. They are not added to model training or a shared user database. See README for installation and Docker commands.

## Session record

- Read existing project documents, inspected source/model/data, and preserved the academic baseline.
- Added connected evidence workflows, imports/manual observations, PDF export, conditional next-day forecasting and pack-change validation.
- Refactored review orchestration and retained actual failures while resolving mutation setup and browser navigation checks.
- Refreshed public evidence and audited the frozen model instead of manufacturing stronger performance claims.
- Updated README, the Claude handoff and this tracker. Completion is judged against the open gates above, not the presence of dashboard cards.

## Second completion pass — in progress

- Data collection now retains immutable public-source snapshots and deduplicates by source observation ID. Re-fetching the same observation never becomes a new observation date. Existing historical snapshots have been archived; the live refreshed INR collection remains 407 records. `history_readiness.csv` exposes missing basis and insufficient histories.
- API cache validation rejects wrong-product and structurally invalid entries. The workspace can read accumulated public evidence. Manual observations still remain session-local.
- Official API investigation: Amazon Creators needs an accepted Associates account; Keepa requires an API key; Flipkart provides an affiliate feed interface. Account availability and deployment host have been requested; no keys were requested in chat, and no paid accounts were created.
- Model development experiment: fixed title-augmented and reference-price-free alternatives trained on 8,502 original training rows and compared on 2,275 disjoint development rows. Original validation/calibration/test rows were excluded. Results are in `reports/current/model_development.json`; the deployed artifact remains unchanged.
- Firefox/WebKit compatibility, concurrent inference checks and release configuration are being completed. Earlier 122-test/current-review measurements above describe the previous pass until regenerated below.
