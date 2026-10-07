# Claude handoff: Price Truth interface polish

> **Historical document.** Superseded; kept for the record. Current status: [PROJECT-COMPLETION.md](../../PROJECT-COMPLETION.md).

> **Completed 7 October 2026.** The redesign described here has been implemented; see PROJECT-COMPLETION.md. This brief is kept for reference.

Copy the prompt below into Claude and provide the project files listed afterward. This is a handoff document; Claude has not been contacted and no files have been uploaded.

## Prompt

You are improving the presentation and usability of an existing, working Price Truth application. The main academic deliverable is a reproducible code review of the real Python codebase. Preserve working behavior and data integrity while making the interface coherent and polished.

Read PROJECT-COMPLETION.md, README.md, PROGRESS.md, docs/DATA-SOURCES.md, docs/REVIEW-SUBMISSION-PLAN.md and reports/current/CODE-REVIEW-REPORT.md first. Treat the September report as historical evidence. Older planning files contain superseded claims; the current implementation and source evidence take precedence. Inspect app.py, src/price_truth/ui.py, src/price_truth/workspace.py and tests/test_workspace_evidence.py before editing.

Use https://price-truth.netlify.app/dashboard as the visual reference and https://price-truth.netlify.app/ for brand context. Preserve its readable sidebar, product search emphasis, spacious cards, soft coral/blue/mint accents and clear comparison charts. Its numbers, charts, search behavior, genuineness score and waiting-period predictions are simulated; do not copy them as working results.

The current app is Streamlit with independent Python domain functions. Improve this interface in place. Do not replace it with a disconnected HTML mockup or migrate frameworks as part of a styling task. If a requested visual interaction requires backend changes, document that dependency explicitly rather than simulating a response.

### What exists

| Component | Working behavior | Boundary |
|---|---|---|
| Catalogue | 21,267 cleaned historical Amazon/Flipkart listings | Not current offers or verified equivalent products |
| Discount Checker | User quote, trained price estimate, calibrated range, real Tree SHAP, JSON and PDF export | No fraud labels or genuineness probability |
| Pack Lookup | Live barcode/name lookup with dated saved fallbacks | Food coverage varies; no connection to catalogue identity has been established |
| Unit Compare | Price/quantity/currency validation and multipack normalization | Currently user-entered options |
| History | Barcode/store/currency/unit filtering and dated observations | Current shipped histories are sparse or stale; no current buy forecast |
| Shrink Timeline | Two attributed Indian pack-change cases | Secondary reports, not a universal product timeline |
| Evidence | Real dataset audit, model evaluation and review reports | Review measurements belong to the recorded code version |

Product Workspace now connects analysis within an explicit evidence identity: catalogue listing to model assessment; food barcode to pack lookup and dated history; structured pack quantity to unit comparison. Manual/CSV observations support dated history, conditional next-day forecasting and confirmed pack changes. These records live in session memory and can be exported or cleared. Cross-source automatic product matching remains unimplemented and must not be implied. In particular, a food lookup record must not be silently matched to an unrelated Amazon listing just to fill the dashboard.

### Interface requirements

1. Place the selected product identity, variant/pack size, platform, currency and source date above any product analysis. Show unknown fields explicitly.
2. Preserve actual input controls, validation, model calls, API calls, exports and computed chart values. Use existing Python functions; do not reimplement calculations in presentation code.
3. Distinguish historical catalogue data, live responses, dated saved responses and manually entered quotes. Show their sources near results.
4. Make one clear primary action per screen. Keep technical method details in expandable areas; retain a plain-language explanation of what the result means.
5. Present unavailable information as useful empty states with an appropriate next action. Use the existing abstention behavior for unsupported predictions. Never substitute a random graph, percentage, waiting period, review count or seller rating.
6. Show exact-product offers separately from comparisons across pack variants. A lower unit price across different sizes is not a lower price for the same exact pack.
7. Keep real SHAP data and explain that it describes the model's estimated historical selling price. Do not label SHAP contributions as causes of dishonesty.
8. Support keyboard use, visible focus, readable contrast, small screens and reduced-motion preferences. Do not rely only on color or motion to convey conclusions.
9. Do not add nonfunctional login, watchlist, history or notification controls. These require real behavior and are not visual decoration.
10. Preserve raw CSVs, external caches, training splits, model artifacts, reports and tests. Synthetic fixtures are allowed for tests only; do not present them as real training evidence or market results. Do not manually alter test counts or performance metrics.

### Acceptance and return handoff

- Run the existing tests. If accessible labels or navigation change intentionally, update the relevant UI tests to check the new real behavior; never remove assertions to hide failures.
- Verify actual desktop and mobile flows, loading, errors, empty data and offline fallback.
- Return the modified code, a list of changed files, screenshots, commands run, results and known unresolved issues.
- Record all added dependencies and setup changes.
- Identify backend dependencies that remain for a unified product dashboard. Do not claim those are implemented if only their visual layout exists.
- Code review must be regenerated after code changes. From the project root, run `.venv/bin/python scripts/review.py`; run `.venv/bin/python scripts/browser_current.py` separately with the local app running, adapting its Chrome path if necessary. If tools cannot run in your environment, say so and leave results for the project owner to regenerate.
- Do not publish or replace the Netlify site as part of this handoff.

## Files to provide

Provide PROJECT-COMPLETION.md, Dockerfile, .dockerignore, README.md, PROGRESS.md, pyproject.toml, requirements.txt, requirements-dev.txt, .streamlit/config.toml, app.py, src/price_truth/, tests/, scripts/, this document, docs/DATA-SOURCES.md, docs/REVIEW-SUBMISSION-PLAN.md and the review report. Include existing screenshots under reports/ as context.

For a runnable local copy, Claude also needs the existing datasets and trusted local model artifact. Keep the supplied raw data within the development workspace; source redistribution rights have not been verified. Do not include .venv/, secrets, credentials or unrelated personal files. A screenshot-only or source-only handoff cannot verify the full app without its runtime dependencies and data.

## October implementation and validation boundaries

The current model audit is `reports/current/model_audit.json`. Held-out MAE is INR 356.82, with material subgroup weaknesses and dependence on the supplied reference price. Do not turn the estimate into an authenticity score. The INR feasibility audit found 407 records and no comparable series reaching 40 dates; no validated current Indian forecast is claimed. Preserve forecast abstention and history basis/pack-continuity checks.

The Docker configuration is supplied but not build-tested locally. Styling may proceed locally; deployment requires choosing a host, verifying data publication permissions, setting HTTPS/storage, and running post-deployment checks. Preserve the prototype site until replacement deployment is explicitly requested. Rerun current review/browser checks after final changes; never reuse old source-bound metrics as new measurements.
