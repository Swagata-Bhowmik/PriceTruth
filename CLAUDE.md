# CLAUDE.md — Price Truth

Context for Claude (and other coding agents) working in this repository. Read this first, then the files it points to. Last updated **7 October 2026**.

## What this project is

**Price Truth** is a Python/Streamlit web app that helps Indian online shoppers judge prices: is a discount genuine, is the price usual for the product, which pack size is better value, has a pack shrunk at the same price (shrinkflation), and where is the product cheapest. It is the **NMIMS M.Sc. Data Science (Semester 3) Group 11 project**, Professor Dr. Yogesh Naik. Swagata Bhowmik is the technical lead and owns this repository.

Course deliverables: Deliverables 1–3 (business need, prototype, presentation) were submitted in August. Lab Work (code review, 40 marks) was submitted on the 19 September code. The **Working Demo (20 marks) is due 16 October 2026**. A static design prototype exists at https://price-truth.netlify.app (simulated data — not this app).

Full background, requirements, personas (Priya, Rajesh, Aarav), rubric and decisions: **`PRICE-TRUTH-MASTER-CONTEXT.md`** (local only — see below).

## Where things are

| Item | Location |
|---|---|
| Repository | https://github.com/Swagata-Bhowmik/PriceTruth (public), branch `main` |
| Source of truth | **This repository only.** No other repository or folder is used |
| Local clone (Windows) | `C:\Users\mrkri\Documents\GitHub\PriceTruth`; venv at `.venv\Scripts\python.exe` (Python 3.12) |
| First commit | `f78958e` (7 Oct 2026, Swagata Bhowmik) — single import commit: *“Import Price Truth application, dataset, models and tests (AI-assisted development)”* |
| CI | GitHub Actions **Application checks** (review, container, browsers) — green on `59f9a8d` |
| Status tracker | `PROJECT-COMPLETION.md` — measured state, decisions in force, open items |
| Online deployment | Not yet. Planned on Streamlit Community Cloud from this repo (README → Deployment) |

## How it was built (history)

1. **Up to 19 Sep 2026 — Codex.** Data pipeline on two Kaggle datasets, gradient-boosting price model with SHAP, eight Streamlit pages, Ruff/PyTest/Mutmut/Radon review; Lab Work report generated from that code.
2. **6 Oct — Codex.** Connected workspace, user observations (manual/CSV), PDF export, gated forecasting, Open Prices collection, model audit, Dockerfile, CI workflow.
3. **7 Oct — Claude (Claude Code session).**
   - **UI redesign**: brand theme, `st.navigation` pages in `views/`, verdict banners, plain-language SHAP (% effects), empty states, mobile layout, accessibility fixes.
   - **Engineering quality**: complexity rank A/B everywhere, mutation scope extended to 8 domain modules, coverage raised, warnings removed.
   - **Dataset finalised (v1.2)**: real fields recovered (Amazon dates from link timestamps, brands from titles, Flipkart zero ratings, variants from specifications), 15 category groups, research-calibrated **synthetic layers** (daily price histories, discount labels, cross-platform offers, food shop histories) with official MoSPI CPI inflation adjustment; discount-authenticity classifier; price model retrained.
   - New Price-check tabs: **Discount check**, **Price history & timing**, **Where to buy**.
   - Code review: 10 findings fixed with regression tests; illustrated **user guide** (`docs/USER-GUIDE.html`, also at `/user-guide` in the app).
   - Automation: daily Open Prices collection, uptime probe, Docker build in CI.
   - Moved to this repository (7 Oct) as one import commit.
4. **8 Oct — Claude (Windows clone).** Repository cleanup (one tracker, `docs/history/`, LF line endings, Windows UTF-8 fixes); **single-page product dashboard** replacing Home/Price check/Unit price/Shrinkflation (dropdown selector, six hover-explained headline cards, sticky section menu, quote-aware offers); structured JSON logging; Bandit SAST in the review; `docs/ARCHITECTURE.md` (framework trade-offs, NFRs); `requirements.lock`; tabs replaced by scrolling sections on detail pages; user guide rebuilt by `scripts/build_user_guide.py`.

## Current measured state (8 Oct 2026, CI evidence for `59f9a8d` in `reports/current/`)

| Check | Result |
|---|---|
| Tests | **416 passing**, no warnings (`pytest -q`) |
| Coverage (package) | 94.83% statements, 87.09% branches |
| Mutation (8 domain modules) | 1,556 / 1,582 killed (**98.36%**); 26 equivalent survivors documented in `docs/MUTATION-SURVIVORS.md` |
| Lint / complexity / security | Ruff clean; every block Radon A or B (tests included); Bandit 0 findings |
| Price model (real data only) | 4,269 held-out listings: **R² 0.959, MAE ₹357, median error 20.8%**; verdict for 99.6% of listings |
| Discount model (synthetic labels) | Logistic regression, ROC AUC **0.88** (secondary check in the UI) |
| Browsers (CI) | Chromium, Firefox, WebKit flows + PDF download pass; no overflow at 390/768/1440 px |
| Speed | warm render 0.24 s server-side; CI-runner load test 25 users median 19.9 s (client-bound) |
| Dataset audit | 59 / 59 integrity checks pass |

Windows note: `scripts/review.py` needs Linux (mutmut). Final evidence comes from the CI artifacts `engineering-evidence` and `browser-evidence`, imported after checking `review_manifest.json` source hashes against the working tree.

## Commands

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe` (and `.venv/bin/ruff` with `.venv\Scripts\ruff.exe`, and so on). Mutmut does not run natively on Windows, so `scripts/review.py` (which includes it) runs in CI or WSL; tests, Ruff and Radon run locally.

```bash
.venv/bin/python -m streamlit run app.py          # app at http://localhost:8501 (guide at /user-guide)
.venv/bin/python -m pytest -q                      # all tests (UI tests run offline)
.venv/bin/ruff check .                             # lint
.venv/bin/radon cc -s -n C src scripts app.py views   # must print nothing (no rank C+)
.venv/bin/python scripts/review.py                 # full review → reports/current/ (includes mutmut, ~3 min)
.venv/bin/python scripts/browser_current.py --browser chrome|firefox|webkit   # needs the app running
.venv/bin/python scripts/load_test.py --users 10 25    # real-browser load test (PRICE_TRUTH_URL to target a host)

# Data and models (only when changing data):
.venv/bin/python -m price_truth.data               # rebuild real catalogue from the raw CSVs
.venv/bin/python -m price_truth.model              # retrain price model (real data only)
.venv/bin/python scripts/model_audit.py            # per-category accuracy → reports/current/model_audit.json
.venv/bin/python scripts/build_final_dataset.py    # synthetic layers + discount model → datasets/final/
```

The `.venv` has an editable install pointing at **this** folder's `src/`. If `price_truth` imports from elsewhere: `.venv/bin/python -m pip install -e . --no-deps`.

## Code map

```text
app.py                 top navigation (st.navigation), theme, logging, warm-up
views/*.py             one line per page: dashboard (home), food, observations, catalogue, methods, user-guide
src/price_truth/
  dashboard.py         the product dashboard: dropdown selector, headline cards, scrolling sections
  ui.py                unit-result and shrinkflation helpers, Catalogue and Methods page bodies
  market_ui.py         listing price histories (cached) and the history chart
  workspace.py         Food & packs, My observations
  theme.py / present.py   design system (CSS, cards, tooltips, section menu) / verdicts, headline cards, SHAP (pure)
  logs.py              structured JSON logging (configured in app.py)
  resources.py         cached catalogue, models, reports; background warm-up
  data.py              raw CSV → datasets/processed/catalogue.csv (recovered fields, categories, variants)
  model.py             price model training, assess() with Tree SHAP
  authenticity.py      discount-authenticity classifier
  synthetic.py         seeded, calibrated generator (histories, labels, offers, food histories, CPI factor)
  calculations.py, catalogue.py, history.py, forecast.py, observations.py, offers.py,
  external.py, price_api.py, evidence_store.py, exports.py, cache.py, paths.py   domain logic
scripts/               review, audits, dataset build, browser/load/uptime checks, data collection
tests/                 PyTest + Streamlit AppTest; test_review_fixes*.py = code-review regressions
datasets/              raw Amazon/Flipkart CSVs (never modified), processed catalogue, external API data, final/
.github/workflows/     checks.yml (CI), collect-prices.yml (daily), uptime.yml (15 min, needs HEALTH_URL)
```

## Data rules — keep these

- **Raw files** in `datasets/amazon/` and `datasets/flipkart/` are never modified; their SHA-256 is checked by tests.
- **Every row has `provenance`**: `real` or `synthetic`. Synthetic layers live in `datasets/final/` and are documented in **`datasets/final/DATA-CARD.md`** (v1.2). Every generator parameter and its source is in `datasets/final/assumptions.json` (values marked `assumption` where no citable figure exists).
- **The price-estimate model trains and evaluates on real listings only.** Synthetic data feeds histories, offers, discount labels and the discount classifier.
- The UI shows synthetic results like real ones (project decision); the **Methods & data → Dataset** tab and exports state provenance. Never present synthetic data as observed fact in reports.
- Never invent pack-size changes for real brands: real shrinkflation cases must be cited; simulated timelines use generic names.
- The generator is deterministic per product key; past days never change when later days are added. Changing `assumptions.json` changes histories → rebuild the dataset and rerun tests.

## Working rules

- Run tests, Ruff and the Radon check after every change. Keep all functions rank A/B.
- Add a test for every bug fix. Domain regression tests belong in `tests/test_review_fixes_domain.py` (included in the mutation run via `pyproject.toml [tool.mutmut]`); UI tests use AppTest and must stay **offline** (`session_state["food_offline"] = True`).
- After code changes that will be reported, rerun `scripts/review.py` and the browser checks; never edit measured numbers by hand.
- Live lookups write cache files under `datasets/external/off`, `price_cache/` and `search/`. Do not commit those incidental files unless intended.
- The user guide (`docs/USER-GUIDE.html`) contains screenshots of the app. If a page changes visibly, regenerate the guide (the capture/build scripts are not in the repo; recreate them with Playwright if needed) or note it as outdated.
- If port 8501 is busy, use `--server.port 8502`.

## Documents — current vs historical

| Current | Historical (describe earlier states; do not treat as current) |
|---|---|
| `README.md` — setup, pages, deployment, automation | `docs/history/` — earlier trackers, plans and handoffs (index in its `README.md`) |
| `PROJECT-COMPLETION.md` — **the one status tracker**: measured state, decisions, open items | `reports/2026-09-19-lab-submission/` — evidence behind the submitted Lab Work report |
| `datasets/final/DATA-CARD.md` — dataset v1.2 | `submission/` (local only; Word reports of 19 Sep) |
| `reports/current/CODE-REVIEW-REPORT.md` + raw evidence | |
| `docs/DATA-SOURCES.md`, `docs/MUTATION-SURVIVORS.md`, `docs/USABILITY-STUDY.md`, `docs/USER-GUIDE.html` | |

`reports/` root holds only live model and data outputs read by the app (`model_evaluation.json`, `data_audit.json`, `discount_model_evaluation.json`, `evaluation_split.csv`). New review evidence goes to `reports/current/`. Status changes go in `PROJECT-COMPLETION.md`; do not start new tracker files.

## Local-only files (not in Git)

Ignored by `.gitignore` because they contain team names and roll numbers or are generated output. They are **not present in the Windows clone**; ask the user for them when needed:

- `PRICE-TRUTH-MASTER-CONTEXT.md` — full project history, requirements, rubric, personas (**read for background**)
- `PRICE-TRUTH-BUILD-HANDOFF.md` — build plan, FR/NFR list
- `PRICE-TRUTH-CODE-REVIEW-SPEC.md` — required contents of the code-review report
- `submission/` (Lab Work Word reports, viva script, ZIPs), `output/` (Deliverable 4 PDF)
- `GITHUB-SETUP.md` — the manual steps used to set up this repository
- Generated: `reports/current/development_*.csv`, `*.stderr`, mutation `.diff` files, `.venv/`, `mutants/`

## Open items

Maintained in **`PROJECT-COMPLETION.md` → Open items** (before-demo list for 16 Oct, then time- or third-party-bound items). Keep that list current instead of duplicating it here.
