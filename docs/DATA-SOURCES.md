# Data sources and modeling decisions

> **Update, 7 October 2026.** The project now also uses research-calibrated **synthetic** layers (daily price histories, discount labels, cross-platform offers and food shop histories), each marked `provenance = synthetic`. See [the dataset card](../datasets/final/DATA-CARD.md). Three fields were recovered from the real data: Amazon dates from link timestamps (5 Jan 2023), Amazon brands from titles, and Flipkart zero rating counts. Statements below about "no synthetic data" describe the price-estimation model, which still uses real listings only.

## Sources actually used

| Source | Provenance | Role | Limits |
|---|---|---|---|
| [Amazon Sales — Karkavelraja J](https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset) | CSV downloaded and supplied by the user; SHA-256 in `reports/data_audit.json` | 1,465 raw rows; 1,347 retained catalogue listings | Undated snapshot; repeated IDs; no seller ratings; no fraud labels |
| [Flipkart Products — PromptCloud](https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products) | CSV downloaded and supplied by the user; SHA-256 in audit | 20,000 raw rows; 19,920 retained listings | 2015–2016 snapshots; ratings mostly unavailable; no useful within-product time series |
| [Open Prices](https://openfoodfacts.github.io/open-prices/guides/data/) | Read-only official API; query, retrieval timestamp, observation IDs, dates and source links saved | Separate INR observation collection and a French-store/EUR history example | INR repeat histories are sparse; EUR example is stale; currencies are never merged or converted |
| [Open Food Facts](https://openfoodfacts.github.io/documentation/docs/Product-Opener/v3/products/get-api-v3-product-code/) | Official barcode API; genuine cached responses retain retrieval dates | Pack lookup with live/cached status | Crowdsourced incomplete fields; live requests may fail; a changed database field is not proof of shrinkflation |
| [Search-a-licious](https://openfoodfacts.github.io/search-a-licious/users/ref-openapi/) | Official full-text search service | Live food-name search with a saved Maggi query | Results are global; an Indian brand name does not imply every result is sold in India |
| [Bloomberg / Financial Express, 13 May 2022](https://www.financialexpress.com/business/industry-shrinkflation-hits-indias-snacks-market-as-companies-cope-with-inflation-and-reduce-size-of-packaging-2523265/lite/) | Attributed factual extraction from reporting | Two documented pack changes: Vim 155g→135g and Haldiram’s aloo bhujia 55g→42g, each at ₹10 | Retailer/distributor reports; exact pack observation dates and barcodes unavailable; no claim of direct inspection |

Open Food Facts/Open Prices collections are ODbL. They remain in a separate directory and are not merged into the Kaggle model-training table. The supplied CSVs do not include license documents; confirm their current source-card licenses before public redistribution. This local build makes no claim that raw-data redistribution has been cleared. Source URLs and hashes establish traceability, not independent verification of every listing.

## Alternatives researched

| Candidate | Decision |
|---|---|
| [Keepa API](https://keepa.com/api-docs/) | Real historical Amazon data is relevant, but requires a subscription and a coverage/use check. No subscription purchased. |
| Additional Flipkart listings | Do not add a second overlapping snapshot merely for row count; the existing catalogue already has substantial category coverage. |
| [Open CDP multi-category events](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) | Real product/event prices, but a different market and large event log; not evidence about Indian marketplace discounts. |
| Generated “Amazon-style” sales datasets | Rejected. Realistic-looking rows do not meet the requirement for real observations. |
| Seasonal sale-calendar lookup | Rejected as empirical prediction: these snapshots cannot establish Diwali or Prime Day effects. |

## Cleaning policy

1. Preserve both original CSVs byte-for-byte; verify SHA-256 on every review.
2. Parse prices and missing ratings separately. Missing ratings stay missing in the catalogue; model-only imputation is explicitly learned from the fitting partition.
3. Reject missing/nonpositive/inverted prices. Quarantine all rows of an ID with conflicting listed or selling prices.
4. Keep the first source row for other repeated platform-specific IDs. This is a deterministic record choice, not a claim it is the latest observation.
5. Preserve source category paths, platform and available dates. Broad category harmonization supports browsing; it does not establish exact product equivalence.
6. Do not copy reviewer names, reviewer IDs, or review text into the processed catalogue.
7. Calculate advertised discount directly from the source prices. Derived arithmetic is not a synthetic observation.

Four Amazon IDs have a price conflict: three have different selling prices, and one additional ID has a different listed reference price. The initial audit discussed selling-price conflicts; the full cleaning check catches both.

## What the trained model means

The target is `log(1 + observed selling price in INR)`. Inputs are listed reference price, available product rating/count, platform and category fields. Selling price, advertised discount, and price-bearing descriptions are excluded from inputs. The model is deliberately a price-estimation baseline, not a classifier trained on invented “fake” labels.

Normalized titles group matching names and some colour variants before splitting. Train, validation, calibration and test partitions have no overlapping title groups. This reduces but does not guarantee elimination of product-family leakage; model numbers should not be interpreted as prospective performance on current listings.

A category/platform median price-ratio baseline, random forest, and histogram gradient boosting were compared. Selection uses validation mean absolute log error, which weights price scales more evenly than rupee error. The selected tree model is refit on train+validation, its interval is calibrated on a separate partition, and final results are reported on held-out products. Separate-platform fits are diagnostic comparisons and do not determine the selected model after test results are seen.

Real `shap.TreeExplainer` values sum to the model prediction in log-price space. They explain estimated selling price, not fraud probability. A high reference price can raise the model estimate; a below-range quote alone cannot establish authenticity. Categories with fewer than 30 fitting records are marked as limited support.

## Honest feature boundaries

- Catalogue search retrieves historical listings on both platforms; it does not claim same-SKU live aggregation.
- History compares the same barcode/store/currency/recorded basis. At least five prior dates, a 14-day span and a latest observation within 90 days are required for a comparative signal. The threshold is an explicit product rule, not a validated forecast model.
- Missing price basis and potential pack changes still require caution. The source never proves unchanged pack size merely by retaining a barcode.
- The shipped INR and EUR histories do not support a current buy/wait prediction. Charts and retrospective comparisons work; abstention is the correct result for insufficient or stale evidence.
- Unit comparison uses real user-entered prices/quantities and requires matching units and currencies. User entries are not added to the training dataset.
- Unit-test boundary fixtures deliberately include invalid inputs and controlled arithmetic examples. They are isolated tests and never enter model training or displayed source evidence.


## 6 October 2026 update

The original snapshots and training artifacts are preserved. A separate normalized refresh at `datasets/external/current/open_prices_inr.json` contains 407 INR observations across 381 barcodes. Its audit is `reports/current/data_feasibility.json`: no comparable group reaches 40 distinct dates, and the maximum is two. Missing price basis and unknown historical pack continuity additionally limit comparability. This does not establish current buying forecasts.

User-supplied manual/CSV observations are explicitly unverified, remain in session memory and can be exported or cleared. They do not automatically become training records. Test fixtures use synthetic observations solely to exercise validation and forecasting behavior. The frozen model audit is `reports/current/model_audit.json`; the active completion record is `PROJECT-COMPLETION.md`.
