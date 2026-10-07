# Price Truth — completion record, 6 October 2026

> **Historical document.** The 6 October record, moved here from PROJECT-COMPLETION.md. Its numbers are superseded. Current status: [PROJECT-COMPLETION.md](../../PROJECT-COMPLETION.md).

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
