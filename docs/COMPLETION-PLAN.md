# Price Truth — full completion plan

Written 7 October 2026. Baseline: the 6 October build (150 passing tests; review manifest matches current source). The goal is a complete, deployed product, not only a demo. The Working Demo is due 16 October; work after that continues toward full completion.

Rules carried over from earlier work: no synthetic data in training, history or offers; no fake scores, waiting periods or ratings in the UI; no unauthorized scraping. Unsupported results should decline with a clear explanation.

---

## 1. Gap audit — what is pending

### A. Interface (largest visible gap)

| # | Problem observed in the current build | Fix |
|---|---|---|
| A1 | Default Streamlit look: no brand colours, logo or icons, and Streamlit's "Deploy" toolbar is visible | Apply the brand theme (purple/lavender + coral + mint, shield mark), hide the toolbar (`client.toolbarMode = "minimal"`), add a small CSS layer and page icons |
| A2 | 9 radio-button pages with duplicated flows: Discount Checker repeats the Workspace listing flow, and Unit Compare appears twice | Use `st.navigation` with grouped pages: **Home** (search) → **Product** (one product view with tabs) → **Tools** (Unit compare, Shrink timeline) → **My data** → **About/Methods**. Remove the duplicates |
| A3 | Raw JSON is shown to users: timing signal and forecast (`st.json`), pack details (`st.write(dict)`), and the Evidence page | Turn these into result cards: verdict badge, key numbers, plain-language explanation, and an expandable "technical detail" section |
| A4 | The SHAP waterfall uses `log(1+price)` units and internal feature names | Convert contributions to ₹ effects, use readable feature labels, use a horizontal bar chart (the Netlify style), and keep the log view in an expander |
| A5 | The assessment verdict is a plain `st.info` with a snake_case status | Add a verdict banner (Below / Within / Above expected range) with icon and colour, so meaning doesn't depend on colour alone, plus a range gauge showing the quote against the model interval |
| A6 | No product header card | Add a product identity card above every analysis: name, platform, category, pack size, currency, source date and data badge (Historical / Live / Saved / User-entered) |
| A7 | Overview is a text list and shows "Generated training records: 0" | Build a real home page: hero, search-first input, four feature cards linking to real flows, and honest data-coverage stats |
| A8 | Empty and error states are plain info boxes | Give each empty state a reason and a next action (e.g. "Not enough history → add observations / try saved example") |
| A9 | Mobile: long titles, truncated product selectbox, results below the fold, price steppers | Use a compact header, a searchable result list instead of a 200-item selectbox, text inputs for prices, and stacked cards |
| A10 | Accessibility not verified | Contrast check on the palette, visible focus, keyboard path through the main flows, `prefers-reduced-motion`; run axe-core in the Playwright browser check |
| A11 | Charts use default styling | Apply one Plotly template for brand colours and fonts, and use it for every chart (history, pack change, unit compare) |
| A12 | The cold first assessment takes 9.3 s (font cache plus first SHAP call) | Warm the model, SHAP explainer and ReportLab at startup with `st.cache_resource`; target under 2 s for the first user |

The Netlify features "Saved products" and "History" are only added in Section D, once real persistence exists, and never as decorative buttons.

### B. Engineering quality

| # | Item | Target |
|---|---|---|
| B1 | Not a git repository, so CI has never run | `git init`, private GitHub repo, `.gitignore` for `.venv`, `mutants/`, caches and large reports; first CI run green |
| B2 | Docker image has never been built | Build in CI (the `container` job already exists) and fix anything that breaks |
| B3 | High complexity: `validate_observations` (CC 15), `forecast_next_day` (14), `lookup_page` (13) | Split into helpers so every function is rank B or better |
| B4 | UI modules are barely tested; `app.py` is outside coverage | Streamlit `AppTest` tests for each page's main flow; include UI modules in coverage; statements ≥ 90%, branches ≥ 85% |
| B5 | Mutation testing covers only 3 modules; 57 survivors | Extend to `observations`, `forecast`, `offers`, `price_api`, `evidence_store`; kill or justify every survivor in writing |
| B6 | Sklearn warning: `log_rating_count` imputer with no observed values | Fix the pipeline input or drop the feature for that path |
| B7 | Docs disagree (PROGRESS says 98 tests, COMPLETION says 122, actual is 150) | One canonical tracker (this plan + PROJECT-COMPLETION); mark the others historical |
| B8 | Dependencies: the dev environment reused an Anaconda install | Clean venv from `requirements*.txt`, `pip check`, lock file for reproducible builds |

### C. Deployment and operations

| # | Item | Notes |
|---|---|---|
| C1 | Pick a host | Recommended: **Hugging Face Spaces (Docker)** or **Render**. Both are free, run our Dockerfile and provide HTTPS. Streamlit Community Cloud also works but ignores the Dockerfile and has limited storage |
| C2 | Licensing before public hosting | Amazon dataset is **CC BY-NC-SA 4.0**, Flipkart is **CC BY-SA 4.0**, Open Food Facts is **ODbL**. Non-commercial academic hosting with attribution is fine; add a visible attribution/licence page. No monetized affiliate links while the NC dataset is bundled |
| C3 | Persistence | Session-only observations are lost on restart. Add SQLite (or a free Postgres such as Neon/Supabase) for saved products and observations; see D2 |
| C4 | Uptime and monitoring | Free uptime monitor (e.g. UptimeRobot) on `/_stcore/health`; record a real 14-day observation window |
| C5 | Real load test | Locust or k6 against the **hosted** URL; measure p95 at 25/50/100 users; report honestly whatever the free tier gives |
| C6 | Browsers and devices | Playwright Chromium/Firefox/WebKit in CI, plus real Safari, Edge and one Android and one iPhone (team members' phones) with screenshots |

### D. Product completeness (features the original requirements promised)

| # | Feature | Status | Real path to completion |
|---|---|---|---|
| D1 | Buy Timing (FR6) | Engine done; declines on all real data | **Start collecting now**: a scheduled GitHub Actions job pulls Open Prices INR daily into the archive, and the team logs prices of ~10 fixed products/stores daily via the existing CSV format. 40 consecutive days → earliest real forecast ~mid-November |
| D2 | Saved products / history (Netlify "You" section) | Missing | Lightweight accounts (Streamlit's built-in OIDC login with Google) and a DB-backed watchlist and personal observations. Optional; only if C3 is done |
| D3 | Cross-platform live prices (FR8 / Aggregator) | Not possible without access | Apply for the **Flipkart Affiliate API** (free) and Amazon Associates/Creators API. If approved, show exact-product offers via official feeds; otherwise keep outbound links only |
| D4 | Model v2 | v1 weak for Flipkart Electronics and Personal care; depends heavily on the listed reference price | Promote the title-augmented candidate only after evaluation on an untouched test set; per-category warnings in the UI where R² < 0 |
| D5 | Shrink timeline (FR7) | 2 cited cases | Add more cited cases (news + Open Food Facts quantity revisions with dates) and the planned in-store photo evidence (30–40 labels) |
| D6 | Pack lookup ↔ catalogue linking | Deliberately unimplemented | Keep it that way; show a manual "this is the same product" confirmation instead of automatic matching |

### E. Academic deliverables

| # | Item |
|---|---|
| E1 | Re-run `scripts/review.py` and the browser checks on the **final** code; regenerate the Word report so its numbers match |
| E2 | 3–5 minute demo video (backup for the 16 Oct demo) |
| E3 | Updated viva Q&A (`START-HERE.md`) covering the new UI, deployment and NFR measurements |
| E4 | Usability study: 5 participants matching the personas (Priya, Rajesh, Aarav), task success and SUS score |

---

## 2. Execution — single day (7 October 2026)

Decisions taken: **Streamlit Community Cloud** hosting from a **public GitHub repo**; **no login/accounts** (D2 and C3 dropped — the app stays account-free, and users keep their data by CSV download/upload).

| Step | Work | Owner | Status |
|---|---|---|---|
| 1 | Git repo, `.gitignore`, docs consolidated (B1, B7, B8) | Claude | ✅ Done |
| 2 | Code quality in parallel: complexity, warnings, mutation scope, tests (B3, B5, B6) | Claude (sub-agent) | ✅ 98.3% mutation kill; app functions rank A/B; warning fixed |
| 3 | UI redesign A1–A12 with `AppTest` tests (B4) | Claude | ✅ Done |
| 4 | Daily Open Prices collection workflow (D1 start); licence/attribution page (C2) | Claude | ✅ Done; first run verified |
| 5 | Push to GitHub → CI (review + Docker build, B2) green | Claude | ✅ Review + Docker jobs green |
| 6 | Deploy on share.streamlit.io (needs the owner's Streamlit login) | **User**, ~3 clicks | ⏳ Waiting on owner |
| 7 | Hosted checks: browsers, load test against the live URL, uptime monitor (C4–C6) | Claude + User for phone check | ✅ Local Chrome/Firefox/WebKit + axe; hosted run after deploy |
| 8 | Re-run review on final code, regenerate report, demo recording, viva notes (E1–E3) | Claude | ✅ Review regenerated (358 tests); demo after deploy |

### Cannot finish today (time- or third-party-bound) — started today
- **D1 forecasts:** need 40 consecutive days of real data. The collection job starts today; earliest validated forecast ≈ 16 November.
- **C4 uptime:** the monitor starts today; a 14-day record completes ≈ 21 October.
- **D3 live retailer prices:** depends on Flipkart/Amazon approving API applications.
- **E4 usability study:** needs 5 real participants; the study kit is in `docs/USABILITY-STUDY.md`.
- **D4 model v2:** promotion needs an untouched new test set; development evidence exists, and the deployed v1 stays with per-category warnings.

## 3. Definition of done

- Deployed on HTTPS at a public URL; health monitor shows ≥ 99% over a recorded 14-day window.
- Every page in the navigation has a working flow, a branded result view, a useful empty state and an `AppTest` test.
- No raw JSON or internal names in the main UI; SHAP shown in ₹ with readable labels.
- First assessment under 2 s on the host; load test results reported at 100 users.
- Ruff clean; statements ≥ 90%, branches ≥ 85%; all functions CC ≤ 10; mutation scope covers all domain modules.
- All 9 NFR categories have a measured result (or an honest "not met") in the final report.
- Review evidence, report and video all correspond to one tagged git release.

## 4. Decisions needed from the team

1. **Host:** Hugging Face Spaces vs Render vs Streamlit Community Cloud.
2. **Accounts and persistence (D2/C3):** build login + saved products, or keep the product account-free?
3. **API applications (D3):** will a team member apply for Flipkart Affiliate / Amazon Associates? Keepa is paid (~€49/month) — yes or no?
4. **Daily data collection (D1):** who logs the 10 products daily for 40+ days?

Answered 7 Oct: host = Streamlit Community Cloud (public repo); accounts = not built.
