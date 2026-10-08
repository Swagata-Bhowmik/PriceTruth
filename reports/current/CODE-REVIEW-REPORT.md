# Price Truth — current engineering review

Generated: 2026-10-08T05:30:44.259270+00:00

Historical submission reports are preserved separately; these results apply to this source manifest.

## Ruff

0 violations under configured rules (command exited successfully).

## PyTest

| Measure | Value |
| --- | --- |
| name | pytest |
| errors | 0 |
| failures | 0 |
| skipped | 0 |
| tests | 416 |
| time | 22.852 |
| timestamp | 2026-10-08T05:29:31.929884+00:00 |
| hostname | runnervmmprz5 |

## Coverage

| Measure | Count | Percentage |
| --- | --- | --- |
| Statements | 1907/2011 | 94.83% |
| Branches | 371/426 | 87.09% |

Coverage scope: price_truth package; scripts and app.py are outside this denominator.

## Mutmut

| Outcome | Count |
| --- | --- |
| killed | 1556 |
| survived | 26 |
| total | 1582 |
| no_tests | 0 |
| skipped | 0 |
| suspicious | 0 |
| timeout | 0 |
| check_was_interrupted_by_user | 0 |
| segfault | 0 |

Kill rate: 98.36% (1556/1582). Scope: calculations.py, catalogue.py, history.py, observations.py, forecast.py, offers.py, evidence_store.py, price_api.py.

Surviving mutants are justified individually in docs/MUTATION-SURVIVORS.md.

## Security (Bandit SAST)

| Severity | Findings |
| --- | --- |
| High | 0 |
| Medium | 0 |
| Low | 0 |

Scanned 4,016 lines in src, app.py, views, scripts; 2 lines carry a justified `# nosec` comment (fixed-argument tool subprocesses, text escaping).

No findings.

## Radon CC

| File | Block | CC | Rank |
| --- | --- | --- | --- |
| src/price_truth/price_api.py | valid_cache | 9 | B |
| src/price_truth/price_api.py | fetch_observations | 8 | B |
| src/price_truth/price_api.py | normalize | 6 | B |
| src/price_truth/price_api.py | _normalize_valid | 4 | A |
| src/price_truth/price_api.py | _saved_response | 3 | A |
| src/price_truth/price_api.py | _live_observations | 3 | A |
| src/price_truth/price_api.py | latest_valid_date | 1 | A |
| src/price_truth/ui.py | show_unit_result | 6 | B |
| src/price_truth/ui.py | dataset_tab | 5 | A |
| src/price_truth/ui.py | quality_section | 4 | A |
| src/price_truth/ui.py | methods_page | 4 | A |
| src/price_truth/ui.py | shrink_cases | 3 | A |
| src/price_truth/ui.py | catalogue_page | 3 | A |
| src/price_truth/ui.py | shrink_points | 2 | A |
| src/price_truth/ui.py | headline_metrics | 1 | A |
| src/price_truth/market_ui.py | history_chart | 3 | A |
| src/price_truth/market_ui.py | slim | 2 | A |
| src/price_truth/market_ui.py | listing_history | 1 | A |
| src/price_truth/market_ui.py | current_price | 1 | A |
| src/price_truth/market_ui.py | quote_history | 1 | A |
| src/price_truth/workspace.py | history_panel | 10 | B |
| src/price_truth/workspace.py | pack_details | 10 | B |
| src/price_truth/workspace.py | food_page | 8 | B |
| src/price_truth/workspace.py | add_or_import | 7 | B |
| src/price_truth/workspace.py | price_collection | 6 | B |
| src/price_truth/workspace.py | price_history_tab | 6 | B |
| src/price_truth/workspace.py | show_forecast | 5 | A |
| src/price_truth/workspace.py | history_example | 5 | A |
| src/price_truth/workspace.py | observation_form | 5 | A |
| src/price_truth/workspace.py | forecast_details | 4 | A |
| src/price_truth/workspace.py | find_food | 4 | A |
| src/price_truth/workspace.py | pack_change_panel | 4 | A |
| src/price_truth/workspace.py | use_pack_for_comparison | 3 | A |
| src/price_truth/workspace.py | dataset_food_products | 3 | A |
| src/price_truth/workspace.py | observations_page | 3 | A |
| src/price_truth/workspace.py | offers_panel | 3 | A |
| src/price_truth/workspace.py | price_chart | 2 | A |
| src/price_truth/workspace.py | show_timing | 2 | A |
| src/price_truth/workspace.py | dataset_food_prices | 2 | A |
| src/price_truth/workspace.py | choose_identity | 2 | A |
| src/price_truth/workspace.py | observation_history | 1 | A |
| src/price_truth/external.py | lookup_product | 7 | B |
| src/price_truth/external.py | search_products | 7 | B |
| src/price_truth/external.py | _cached_result | 5 | A |
| src/price_truth/external.py | _lookup_fallback | 5 | A |
| src/price_truth/external.py | cached_products | 5 | A |
| src/price_truth/external.py | get_json | 3 | A |
| src/price_truth/external.py | _search_hits | 2 | A |
| src/price_truth/external.py | _search_summary | 2 | A |
| src/price_truth/history.py | timing_signal | 7 | B |
| src/price_truth/history.py | load_observations | 4 | A |
| src/price_truth/history.py | series_for | 1 | A |
| src/price_truth/catalogue.py | safe_url | 9 | B |
| src/price_truth/catalogue.py | export_csv | 4 | A |
| src/price_truth/catalogue.py | search | 3 | A |
| src/price_truth/present.py | shap_effects | 8 | B |
| src/price_truth/present.py | feature_group | 7 | B |
| src/price_truth/present.py | readable_feature | 6 | B |
| src/price_truth/present.py | top_contributions | 6 | B |
| src/price_truth/present.py | category_quality | 6 | B |
| src/price_truth/present.py | risk_card | 4 | A |
| src/price_truth/present.py | best_offer_card | 4 | A |
| src/price_truth/present.py | basis_note | 3 | A |
| src/price_truth/present.py | saving_card | 3 | A |
| src/price_truth/present.py | money | 3 | A |
| src/price_truth/present.py | price_card | 2 | A |
| src/price_truth/present.py | discount_card | 2 | A |
| src/price_truth/present.py | verdict | 1 | A |
| src/price_truth/present.py | estimate_card | 1 | A |
| src/price_truth/present.py | kpi_cards | 1 | A |
| src/price_truth/resources.py | discount_model | 2 | A |
| src/price_truth/resources.py | report | 2 | A |
| src/price_truth/resources.py | json_file | 2 | A |
| src/price_truth/resources.py | _warm | 2 | A |
| src/price_truth/resources.py | catalogue | 1 | A |
| src/price_truth/resources.py | model | 1 | A |
| src/price_truth/resources.py | start_warmup | 1 | A |
| src/price_truth/offers.py | compare_observed_offers | 7 | B |
| src/price_truth/offers.py | require_same_pack | 5 | A |
| src/price_truth/dashboard.py | packs_section | 9 | B |
| src/price_truth/dashboard.py | selector | 6 | B |
| src/price_truth/dashboard.py | product_heading | 6 | B |
| src/price_truth/dashboard.py | shrink_section | 6 | B |
| src/price_truth/dashboard.py | narrow | 5 | A |
| src/price_truth/dashboard.py | dashboard_page | 5 | A |
| src/price_truth/dashboard.py | rule_verdict | 4 | A |
| src/price_truth/dashboard.py | history_section | 4 | A |
| src/price_truth/dashboard.py | discount_section | 3 | A |
| src/price_truth/dashboard.py | product_label | 2 | A |
| src/price_truth/dashboard.py | analyse | 2 | A |
| src/price_truth/dashboard.py | verdict_section | 2 | A |
| src/price_truth/dashboard.py | timing_card | 2 | A |
| src/price_truth/dashboard.py | offers_chart | 2 | A |
| src/price_truth/dashboard.py | buy_section | 2 | A |
| src/price_truth/dashboard.py | export_section | 2 | A |
| src/price_truth/dashboard.py | options_by_count | 1 | A |
| src/price_truth/dashboard.py | price_inputs | 1 | A |
| src/price_truth/dashboard.py | run_assessment | 1 | A |
| src/price_truth/dashboard.py | pack_row | 1 | A |
| src/price_truth/calculations.py | compare_packs | 8 | B |
| src/price_truth/calculations.py | unit_price | 6 | B |
| src/price_truth/calculations.py | positive | 3 | A |
| src/price_truth/calculations.py | discount_percent | 2 | A |
| src/price_truth/calculations.py | shrink_change | 1 | A |
| src/price_truth/evidence_store.py | accumulated_observations | 9 | B |
| src/price_truth/evidence_store.py | archive_snapshot | 6 | B |
| src/price_truth/evidence_store.py | history_readiness | 3 | A |
| src/price_truth/model.py | train_model | 5 | A |
| src/price_truth/model.py | assess | 5 | A |
| src/price_truth/model.py | observed_numeric | 3 | A |
| src/price_truth/model.py | comparison_basis | 3 | A |
| src/price_truth/model.py | baseline | 2 | A |
| src/price_truth/model.py | with_group_support | 2 | A |
| src/price_truth/model.py | features | 1 | A |
| src/price_truth/model.py | split_groups | 1 | A |
| src/price_truth/model.py | preprocessing | 1 | A |
| src/price_truth/model.py | _preprocessing | 1 | A |
| src/price_truth/model.py | metrics | 1 | A |
| src/price_truth/model.py | load_model | 1 | A |
| src/price_truth/theme.py | contribution_chart | 7 | B |
| src/price_truth/theme.py | effects_chart | 5 | A |
| src/price_truth/theme.py | product_header | 4 | A |
| src/price_truth/theme.py | kpis | 3 | A |
| src/price_truth/theme.py | product_card | 3 | A |
| src/price_truth/theme.py | intro | 2 | A |
| src/price_truth/theme.py | section_nav | 2 | A |
| src/price_truth/theme.py | source_badge | 2 | A |
| src/price_truth/theme.py | range_chart | 2 | A |
| src/price_truth/theme.py | gauge | 2 | A |
| src/price_truth/theme.py | apply | 1 | A |
| src/price_truth/theme.py | hero | 1 | A |
| src/price_truth/theme.py | page_header | 1 | A |
| src/price_truth/theme.py | section | 1 | A |
| src/price_truth/theme.py | footer | 1 | A |
| src/price_truth/theme.py | verdict | 1 | A |
| src/price_truth/theme.py | empty_state | 1 | A |
| src/price_truth/theme.py | stat | 1 | A |
| src/price_truth/theme.py | chart_template | 1 | A |
| src/price_truth/theme.py | style_figure | 1 | A |
| src/price_truth/authenticity.py | train | 6 | B |
| src/price_truth/authenticity.py | assess_discount | 3 | A |
| src/price_truth/authenticity.py | features | 1 | A |
| src/price_truth/authenticity.py | preprocessing | 1 | A |
| src/price_truth/authenticity.py | scores | 1 | A |
| src/price_truth/authenticity.py | label_rule | 1 | A |
| src/price_truth/authenticity.py | best_threshold | 1 | A |
| src/price_truth/authenticity.py | load | 1 | A |
| src/price_truth/logs.py | JsonFormatter | 5 | A |
| src/price_truth/logs.py | format | 4 | A |
| src/price_truth/logs.py | configure | 3 | A |
| src/price_truth/exports.py | assessment_pdf | 4 | A |
| src/price_truth/forecast.py | _history_gate | 9 | B |
| src/price_truth/forecast.py | forecast_next_day | 5 | A |
| src/price_truth/forecast.py | _predict | 3 | A |
| src/price_truth/forecast.py | _backtest | 3 | A |
| src/price_truth/forecast.py | _errors | 2 | A |
| src/price_truth/forecast.py | _clean_history | 1 | A |
| src/price_truth/observations.py | pack_changes | 10 | B |
| src/price_truth/observations.py | evidence_url | 7 | B |
| src/price_truth/observations.py | _clean_text | 6 | B |
| src/price_truth/observations.py | _require_shape | 4 | A |
| src/price_truth/observations.py | _clean_dates | 4 | A |
| src/price_truth/observations.py | validate_observations | 3 | A |
| src/price_truth/observations.py | read_csv | 3 | A |
| src/price_truth/observations.py | _clean_amounts | 2 | A |
| src/price_truth/observations.py | daily_series | 2 | A |
| src/price_truth/synthetic.py | offers_for | 8 | B |
| src/price_truth/synthetic.py | days_until_next_event | 7 | B |
| src/price_truth/synthetic.py | _sales | 5 | A |
| src/price_truth/synthetic.py | reference_check | 5 | A |
| src/price_truth/synthetic.py | sale_mask | 4 | A |
| src/price_truth/synthetic.py | price_level_factor | 3 | A |
| src/price_truth/synthetic.py | price_history | 3 | A |
| src/price_truth/synthetic.py | offers_with_quote | 3 | A |
| src/price_truth/synthetic.py | food_history | 3 | A |
| src/price_truth/synthetic.py | labelled_examples | 2 | A |
| src/price_truth/synthetic.py | recent_window | 2 | A |
| src/price_truth/synthetic.py | assumptions | 1 | A |
| src/price_truth/synthetic.py | seed_for | 1 | A |
| src/price_truth/synthetic.py | category_params | 1 | A |
| src/price_truth/synthetic.py | _charm | 1 | A |
| src/price_truth/synthetic.py | _regular_path | 1 | A |
| src/price_truth/synthetic.py | full_history | 1 | A |
| src/price_truth/data.py | normalize | 10 | B |
| src/price_truth/data.py | flipkart_variant | 7 | B |
| src/price_truth/data.py | category_parts | 5 | A |
| src/price_truth/data.py | spec_value | 3 | A |
| src/price_truth/data.py | amazon_variant | 3 | A |
| src/price_truth/data.py | title_category | 3 | A |
| src/price_truth/data.py | build_catalogue | 2 | A |
| src/price_truth/data.py | load_catalogue | 2 | A |
| src/price_truth/data.py | numeric | 1 | A |
| src/price_truth/data.py | name_group | 1 | A |
| src/price_truth/data.py | amazon_observed_at | 1 | A |
| src/price_truth/data.py | title_brand | 1 | A |
| src/price_truth/data.py | clean_source | 1 | A |
| src/price_truth/cache.py | read_json | 3 | A |
| src/price_truth/cache.py | fresh | 3 | A |
| src/price_truth/cache.py | write_json | 2 | A |
| scripts/review_current.py | metrics_sections | 6 | B |
| scripts/review_current.py | security_scan | 4 | A |
| scripts/review_current.py | source_manifest | 4 | A |
| scripts/review_current.py | security_section | 4 | A |
| scripts/review_current.py | mutation_scope | 2 | A |
| scripts/review_current.py | execute | 2 | A |
| scripts/review_current.py | collect_checks | 2 | A |
| scripts/review_current.py | benchmark | 2 | A |
| scripts/review_current.py | collect_mutations | 1 | A |
| scripts/review_current.py | table | 1 | A |
| scripts/review_current.py | render_report | 1 | A |
| scripts/review_current.py | main | 1 | A |
| scripts/build_final_dataset.py | food_prices | 5 | A |
| scripts/build_final_dataset.py | shrink_cases | 5 | A |
| scripts/build_final_dataset.py | main | 5 | A |
| scripts/build_final_dataset.py | stratified | 2 | A |
| scripts/model_audit.py | main | 5 | A |
| scripts/uptime_report.py | main | 7 | B |
| scripts/model_development.py | main | 5 | A |
| scripts/model_development.py | estimator | 1 | A |
| scripts/model_development.py | experiments | 1 | A |
| scripts/browser_current.py | main | 7 | B |
| scripts/browser_current.py | split_messages | 6 | B |
| scripts/browser_current.py | accessibility | 5 | A |
| scripts/browser_current.py | launch | 4 | A |
| scripts/browser_current.py | check_unit | 3 | A |
| scripts/browser_current.py | check_dashboard | 2 | A |
| scripts/browser_current.py | check_viewports | 2 | A |
| scripts/browser_current.py | run_flows | 2 | A |
| scripts/browser_current.py | visit | 1 | A |
| scripts/browser_current.py | check_food | 1 | A |
| scripts/concurrency_check.py | main | 9 | B |
| scripts/build_user_guide.py | capture | 4 | A |
| scripts/build_user_guide.py | shot | 3 | A |
| scripts/build_user_guide.py | build | 3 | A |
| scripts/build_user_guide.py | figure | 2 | A |
| scripts/build_user_guide.py | scroll_to | 1 | A |
| scripts/build_user_guide.py | main | 1 | A |
| scripts/load_test.py | wave | 9 | B |
| scripts/load_test.py | main | 3 | A |
| scripts/load_test.py | user | 2 | A |
| scripts/data_feasibility.py | main | 5 | A |
| scripts/fetch_real_data.py | fetch_prices | 6 | B |
| scripts/fetch_real_data.py | main | 5 | A |
| tests/test_data.py | test_catalogue_invariants | 9 | B |
| tests/test_data.py | test_build_catalogue_reproduces_shipped_catalogue | 7 | B |
| tests/test_data.py | test_variant_and_brand_recovered_from_source_text | 6 | B |
| tests/test_data.py | test_raw_hashes_and_partition | 4 | A |
| tests/test_data.py | test_evaluation_groups_do_not_overlap | 4 | A |
| tests/test_data.py | test_category_groups_cover_source_roots | 4 | A |
| tests/test_data.py | test_conflicting_actual_source_prices_are_quarantined | 3 | A |
| tests/test_data.py | test_numeric_missing_is_not_zero | 3 | A |
| tests/test_data.py | test_category_rejects_invalid_structure | 2 | A |
| tests/test_data.py | test_title_category_rules | 2 | A |
| tests/test_data.py | test_no_target_leakage_in_features | 1 | A |
| tests/test_forecast.py | test_local_trend_uses_fourteen_values_and_floor | 6 | B |
| tests/test_forecast.py | test_constant_prices_prefer_the_baseline | 6 | B |
| tests/test_forecast.py | test_rolling_median_can_win_and_forecasts_with_itself | 6 | B |
| tests/test_forecast.py | test_selected_method_that_loses_on_test_is_not_promoted | 6 | B |
| tests/test_forecast.py | test_last_observation_must_be_today_or_yesterday | 6 | B |
| tests/test_forecast.py | test_last_price_and_rolling_median_windows | 5 | A |
| tests/test_forecast.py | test_validation_and_test_windows_are_the_last_twenty_days | 5 | A |
| tests/test_forecast.py | test_equal_test_error_is_not_an_improvement | 5 | A |
| tests/test_forecast.py | test_errors_are_one_step_absolute_and_expanding | 4 | A |
| tests/test_forecast.py | test_trend_is_selected_and_reported | 4 | A |
| tests/test_forecast.py | test_unsorted_and_string_input_is_cleaned | 3 | A |
| tests/test_forecast.py | test_invalid_history | 3 | A |
| tests/test_forecast.py | test_forty_days_is_the_minimum | 3 | A |
| tests/test_forecast.py | test_extra_columns_are_ignored | 2 | A |
| tests/test_forecast.py | test_duplicate_dates_are_invalid | 2 | A |
| tests/test_forecast.py | test_missing_days_are_not_interpolated | 2 | A |
| tests/test_forecast.py | test_default_today | 2 | A |
| tests/test_forecast.py | daily | 1 | A |
| tests/test_offers.py | test_confirmation_message_and_result_contract | 5 | A |
| tests/test_offers.py | test_comparison_respects_dates_packs_and_conditions | 4 | A |
| tests/test_offers.py | test_latest_quote_per_store_and_duplicate_links | 4 | A |
| tests/test_offers.py | test_equal_prices_order_by_store_and_dense_rank | 3 | A |
| tests/test_offers.py | test_same_day_price_conflict_and_ties | 2 | A |
| tests/test_offers.py | test_yesterday_counts_and_older_quotes_do_not | 2 | A |
| tests/test_offers.py | test_explicit_today_is_used_for_validation | 2 | A |
| tests/test_offers.py | test_rank_is_an_integer | 2 | A |
| tests/test_offers.py | test_default_today_and_conflict_message | 2 | A |
| tests/test_offers.py | quotes | 1 | A |
| tests/test_offers.py | test_incompatible_quotes_rejected | 1 | A |
| tests/test_offers.py | test_quantities_must_match_exactly_and_dimension_message | 1 | A |
| tests/test_offers.py | test_tiny_pack_differences_are_not_absorbed_by_absolute_tolerance | 1 | A |
| tests/test_offers.py | test_single_quote_is_not_a_comparison | 1 | A |
| tests/test_price_api.py | test_live_fetch_requests_filters_and_saves | 8 | B |
| tests/test_price_api.py | test_normalize_optional_fields | 6 | B |
| tests/test_price_api.py | test_valid_cache_rejects_missing_keys | 6 | B |
| tests/test_price_api.py | test_fresh_cache_is_served_without_network | 5 | A |
| tests/test_price_api.py | test_stale_cache_offline_and_after_failure | 5 | A |
| tests/test_price_api.py | test_normalize_accepts_today_and_rejects_bad_values | 4 | A |
| tests/test_price_api.py | test_valid_cache_accepts_schema_valid_record | 4 | A |
| tests/test_price_api.py | test_normalize_maps_every_retained_field | 2 | A |
| tests/test_price_api.py | test_valid_cache_rejects_bad_metadata | 2 | A |
| tests/test_price_api.py | test_valid_cache_rejects_bad_rows | 2 | A |
| tests/test_price_api.py | test_complete_query_reflects_page_count | 2 | A |
| tests/test_price_api.py | test_numeric_product_codes_are_compared_as_text | 2 | A |
| tests/test_price_api.py | test_stale_cache_is_refreshed_when_online | 2 | A |
| tests/test_price_api.py | test_malformed_live_payloads_are_failures | 2 | A |
| tests/test_price_api.py | item | 1 | A |
| tests/test_price_api.py | record | 1 | A |
| tests/test_price_api.py | cache_root | 1 | A |
| tests/test_price_api.py | offline_network | 1 | A |
| tests/test_price_api.py | test_barcode_is_validated_before_any_io | 1 | A |
| tests/test_price_api.py | test_offline_without_cache | 1 | A |
| tests/test_price_api.py | test_invalid_cache_is_ignored | 1 | A |
| tests/test_services.py | test_history_sparse_stale_and_future | 6 | B |
| tests/test_services.py | test_real_history_stays_in_one_store_currency_and_product | 5 | A |
| tests/test_services.py | test_history_filters_incompatible_or_unproven_observations | 5 | A |
| tests/test_services.py | test_timing_quartile_boundaries | 5 | A |
| tests/test_services.py | test_timing_signal_result_keys_and_messages | 5 | A |
| tests/test_services.py | test_offline_and_timeout_use_real_cache | 4 | A |
| tests/test_services.py | test_collection_selection_and_metadata | 4 | A |
| tests/test_services.py | test_success_saves_real_response | 3 | A |
| tests/test_services.py | test_literal_search_and_empty_platforms | 3 | A |
| tests/test_services.py | test_safe_link_and_export | 3 | A |
| tests/test_services.py | test_history_same_day_median_and_sorting | 3 | A |
| tests/test_services.py | test_search_multiple_words_case_and_platform | 3 | A |
| tests/test_services.py | test_timing_same_day_quote_excluded_and_short_span | 3 | A |
| tests/test_services.py | test_reject_unsafe_links | 2 | A |
| tests/test_services.py | test_history_default_unit_matches_explicit_unit | 2 | A |
| tests/test_services.py | test_history_includes_today_but_excludes_zero_prices | 2 | A |
| tests/test_services.py | test_history_freshness_exact_boundary | 2 | A |
| tests/test_services.py | test_export_neutralizes_spreadsheet_formula_prefixes | 2 | A |
| tests/test_services.py | test_malformed_and_credential_links_are_not_exposed | 2 | A |
| tests/test_services.py | test_both_source_retailer_links_remain_available | 2 | A |
| tests/test_services.py | test_username_or_password_alone_is_rejected | 2 | A |
| tests/test_services.py | test_export_exact_bytes_leave_safe_values_untouched | 2 | A |
| tests/test_services.py | test_history_reads_the_documented_files | 2 | A |
| tests/test_services.py | test_history_keeps_prices_below_one | 2 | A |
| tests/test_services.py | test_invalid_barcode_never_calls_network | 1 | A |
| tests/test_services.py | test_not_found_and_missing_cache | 1 | A |
| tests/test_services.py | test_unknown_barcode_is_reported_as_not_found | 1 | A |
| tests/test_search.py | test_search_requests_and_filters_hits | 5 | A |
| tests/test_search.py | test_search_success_and_timeout | 4 | A |
| tests/test_search.py | test_fresh_lookup_cache_is_reused | 4 | A |
| tests/test_search.py | test_failed_cache_write_keeps_previous_entry | 4 | A |
| tests/test_search.py | test_api_calls_are_logged_as_structured_events | 4 | A |
| tests/test_search.py | test_real_saved_name_search | 3 | A |
| tests/test_search.py | test_get_json_is_bounded_and_rejects_non_objects | 3 | A |
| tests/test_search.py | FakeResponse | 3 | A |
| tests/test_search.py | test_search_outage_falls_back_to_stale_saved_results | 2 | A |
| tests/test_search.py | __init__ | 2 | A |
| tests/test_search.py | raise_for_status | 2 | A |
| tests/test_search.py | test_invalid_search | 1 | A |
| tests/test_search.py | test_search_rejects_malformed_hits_and_missing_offline_cache | 1 | A |
| tests/test_search.py | json | 1 | A |
| tests/test_evidence_store.py | test_history_readiness_groups_and_orders | 10 | B |
| tests/test_evidence_store.py | test_repeated_collection_never_manufactures_history | 6 | B |
| tests/test_evidence_store.py | test_snapshot_name_is_content_hash_and_existing_file_is_kept | 5 | A |
| tests/test_evidence_store.py | test_latest_revision_follows_retrieval_time_not_file_name | 5 | A |
| tests/test_evidence_store.py | test_empty_archive_metadata | 4 | A |
| tests/test_evidence_store.py | test_distinct_ids_in_one_snapshot_are_kept | 3 | A |
| tests/test_evidence_store.py | test_schema_corrupt_and_wrong_identity_caches_are_not_evidence | 2 | A |
| tests/test_evidence_store.py | test_snapshot_requirements | 2 | A |
| tests/test_evidence_store.py | snapshot | 1 | A |
| tests/test_evidence_store.py | test_incomplete_archive_is_explicit_error | 1 | A |
| tests/test_evidence_store.py | test_snapshot_rejects_non_finite_values | 1 | A |
| tests/test_evidence_store.py | test_archived_snapshot_without_rows_is_invalid | 1 | A |
| tests/test_workspace_evidence.py | test_forecast_chronological_holdout_and_future_gate | 7 | B |
| tests/test_workspace_evidence.py | test_manual_observation_validation_and_clear | 7 | B |
| tests/test_workspace_evidence.py | test_workspace_quote_comparison_uses_confirmed_session_evidence | 7 | B |
| tests/test_workspace_evidence.py | test_forecast_abstains_for_constant_sparse_stale_and_bad_history | 6 | B |
| tests/test_workspace_evidence.py | test_csv_preserves_identity_and_labels_evidence | 4 | A |
| tests/test_workspace_evidence.py | test_price_api_filters_identity_and_contributor_fields | 4 | A |
| tests/test_workspace_evidence.py | test_cache_corruption_is_a_miss_and_write_replaces | 4 | A |
| tests/test_workspace_evidence.py | test_pack_change_needs_confirmation_and_identity | 3 | A |
| tests/test_workspace_evidence.py | test_daily_series_requires_same_pack_and_aggregates_dates | 3 | A |
| tests/test_workspace_evidence.py | test_observations_and_food_pages_render_empty_states | 3 | A |
| tests/test_workspace_evidence.py | labelled | 3 | A |
| tests/test_workspace_evidence.py | records | 2 | A |
| tests/test_workspace_evidence.py | test_import_bounds_and_schema | 2 | A |
| tests/test_workspace_evidence.py | test_pdf_export_is_generated_in_memory | 2 | A |
| tests/test_workspace_evidence.py | add_manual_observation | 2 | A |
| tests/test_workspace_evidence.py | test_import_rejects_entire_invalid_batch | 1 | A |
| tests/test_workspace_evidence.py | trend | 1 | A |
| tests/test_workspace_evidence.py | observations_app | 1 | A |
| tests/test_workspace_evidence.py | test_pack_changes_rejects_ambiguous_same_day_evidence | 1 | A |
| tests/test_present.py | test_kpi_cards_follow_results_in_reading_order | 9 | B |
| tests/test_present.py | test_kpi_cards_handle_missing_model_and_no_offers | 6 | B |
| tests/test_present.py | test_verdict_tables_cover_every_domain_status | 5 | A |
| tests/test_present.py | test_basis_note_names_the_comparison_used | 5 | A |
| tests/test_present.py | test_one_hot_columns_are_merged_under_the_listing_value | 4 | A |
| tests/test_present.py | test_small_effects_are_grouped_as_other_factors | 4 | A |
| tests/test_present.py | test_money_formatting | 4 | A |
| tests/test_present.py | test_category_quality_flags_only_weak_groups | 4 | A |
| tests/test_present.py | test_effects_multiply_back_to_the_estimate | 3 | A |
| tests/test_present.py | result | 2 | A |
| tests/test_present.py | test_readable_feature_names | 2 | A |
| tests/test_observations.py | test_daily_series_identity_and_median | 6 | B |
| tests/test_observations.py | test_valid_import_is_normalized_sorted_and_labelled | 4 | A |
| tests/test_observations.py | test_pack_change_converts_units_and_reports_sources | 4 | A |
| tests/test_observations.py | test_sort_uses_identity_before_date | 3 | A |
| tests/test_observations.py | test_extra_columns_are_dropped_and_input_untouched | 3 | A |
| tests/test_observations.py | test_row_bounds | 3 | A |
| tests/test_observations.py | test_read_csv_preserves_text_and_validates | 3 | A |
| tests/test_observations.py | test_read_csv_reads_all_allowed_rows_and_rejects_more | 3 | A |
| tests/test_observations.py | test_pack_change_converts_the_later_pack_too | 3 | A |
| tests/test_observations.py | frame | 2 | A |
| tests/test_observations.py | test_evidence_url_accepts_https_and_strips | 2 | A |
| tests/test_observations.py | test_missing_columns_message_lists_all_columns | 2 | A |
| tests/test_observations.py | test_text_length_limit_is_inclusive | 2 | A |
| tests/test_observations.py | test_units_are_case_insensitive | 2 | A |
| tests/test_observations.py | test_dates_must_exist_and_not_be_future | 2 | A |
| tests/test_observations.py | test_default_today_is_the_current_date | 2 | A |
| tests/test_observations.py | test_conflicting_names_for_one_product_id | 2 | A |
| tests/test_observations.py | test_pack_change_same_day_duplicates_collapse | 2 | A |
| tests/test_observations.py | test_pack_change_same_day_conflicts | 2 | A |
| tests/test_observations.py | row | 1 | A |
| tests/test_observations.py | validate | 1 | A |
| tests/test_observations.py | test_evidence_url_rejects_unsafe_links | 1 | A |
| tests/test_observations.py | test_required_text_columns | 1 | A |
| tests/test_observations.py | test_currency_must_be_three_letters | 1 | A |
| tests/test_observations.py | test_unknown_unit_rejected | 1 | A |
| tests/test_observations.py | test_dates_must_be_iso_format | 1 | A |
| tests/test_observations.py | test_amounts_must_be_finite_and_positive | 1 | A |
| tests/test_observations.py | test_amount_overflow_is_a_validation_error | 1 | A |
| tests/test_observations.py | test_read_csv_size_limit_is_inclusive | 1 | A |
| tests/test_observations.py | test_read_csv_unparseable | 1 | A |
| tests/test_observations.py | history | 1 | A |
| tests/test_observations.py | test_pack_change_requires_confirmation | 1 | A |
| tests/test_observations.py | test_pack_change_single_identity | 1 | A |
| tests/test_observations.py | test_pack_change_rejects_empty_and_mixed_dimensions | 1 | A |
| tests/test_model.py | test_sparse_subcategory_falls_back_to_category_group | 7 | B |
| tests/test_model.py | test_shap_reconstructs_actual_prediction | 5 | A |
| tests/test_model.py | test_training_pipeline_on_real_data | 5 | A |
| tests/test_model.py | test_missing_rating_does_not_break_inference | 2 | A |
| tests/test_model.py | test_invalid_quote_and_sparse_category | 2 | A |
| tests/test_model.py | bundle | 1 | A |
| tests/test_logs.py | test_json_formatter_includes_extra_fields_and_exceptions | 6 | B |
| tests/test_logs.py | test_configure_is_idempotent | 4 | A |
| tests/test_review_fixes.py | test_new_search_resets_the_selected_row | 6 | B |
| tests/test_review_fixes.py | test_quote_replaces_todays_row_in_the_reference_window | 3 | A |
| tests/test_review_fixes.py | test_empty_food_search_shows_no_matches | 3 | A |
| tests/test_review_fixes.py | test_price_collection_reads_files_once | 3 | A |
| tests/test_review_fixes.py | test_pdf_is_built_only_on_download | 3 | A |
| tests/test_review_fixes.py | test_warmup_reuses_cached_objects | 2 | A |
| tests/test_review_fixes.py | app | 1 | A |
| tests/test_review_fixes_domain.py | test_one_bad_row_does_not_discard_a_live_fetch | 4 | A |
| tests/test_review_fixes_domain.py | test_all_malformed_rows_count_as_an_outage | 4 | A |
| tests/test_review_fixes_domain.py | test_require_same_pack_compares_normalised_quantities | 4 | A |
| tests/test_review_fixes_domain.py | test_normalize_valid_skips_and_counts_bad_rows_for_this_barcode_only | 3 | A |
| tests/test_review_fixes_domain.py | test_saved_responses_accept_tomorrow_dated_rows | 3 | A |
| tests/test_review_fixes_domain.py | test_observations_load_as_utf8_on_every_platform | 3 | A |
| tests/test_review_fixes_domain.py | test_latest_valid_date_allows_exactly_one_day_of_skew | 2 | A |
| tests/test_review_fixes_domain.py | quotes | 2 | A |
| tests/test_review_fixes_domain.py | test_old_quotes_of_another_size_do_not_block_ranking | 2 | A |
| tests/test_review_fixes_domain.py | test_valid_archive_still_loads | 2 | A |
| tests/test_review_fixes_domain.py | test_corrupt_saved_products_are_skipped | 2 | A |
| tests/test_review_fixes_domain.py | test_unknown_barcode_with_saved_copy_serves_the_copy | 2 | A |
| tests/test_review_fixes_domain.py | item | 1 | A |
| tests/test_review_fixes_domain.py | quote | 1 | A |
| tests/test_review_fixes_domain.py | test_recent_quotes_of_different_sizes_are_still_rejected | 1 | A |
| tests/test_review_fixes_domain.py | test_malformed_archive_snapshot_is_a_handled_error | 1 | A |
| tests/test_synthetic.py | test_offers_with_quote_use_the_shoppers_price_on_its_own_platform | 7 | B |
| tests/test_synthetic.py | test_history_is_consecutive_daily_positive_and_labelled | 5 | A |
| tests/test_synthetic.py | test_sale_events_follow_the_platform_calendar | 5 | A |
| tests/test_synthetic.py | test_offers_rank_by_total_cost_and_include_own_platform | 5 | A |
| tests/test_synthetic.py | test_classifier_trains_reports_and_explains | 5 | A |
| tests/test_synthetic.py | test_price_level_factor_uses_official_cpi | 5 | A |
| tests/test_synthetic.py | test_history_is_deterministic_and_stable_over_time | 4 | A |
| tests/test_synthetic.py | test_labelled_examples_cover_sale_days_and_mark_inflators | 4 | A |
| tests/test_synthetic.py | test_food_history_is_anchored_and_shaped_like_open_prices | 4 | A |
| tests/test_synthetic.py | test_rule_flags_a_bigger_discount_without_a_real_price_drop | 3 | A |
| tests/test_synthetic.py | test_rule_accepts_a_real_price_drop_and_a_usual_discount | 3 | A |
| tests/test_synthetic.py | test_next_event_is_in_the_future | 3 | A |
| tests/test_synthetic.py | test_history_is_anchored_to_the_real_catalogue_price | 2 | A |
| tests/test_synthetic.py | history | 2 | A |
| tests/test_synthetic.py | test_rule_uses_prices_from_before_the_promotion | 2 | A |
| tests/test_synthetic.py | test_history_starts_from_the_inflation_adjusted_price | 2 | A |
| tests/test_calculations.py | test_multipack_and_dimension | 4 | A |
| tests/test_calculations.py | test_compare_rank_and_no_mutation | 4 | A |
| tests/test_calculations.py | test_discount_from_actual_amazon_listing | 3 | A |
| tests/test_calculations.py | test_unit_conversions | 3 | A |
| tests/test_calculations.py | test_comparison_respects_multipack_count | 3 | A |
| tests/test_calculations.py | test_reported_vim_shrinkage | 3 | A |
| tests/test_calculations.py | test_shrinkage_accounts_for_price_change | 3 | A |
| tests/test_calculations.py | test_positive_preserves_amount | 2 | A |
| tests/test_calculations.py | test_currency_normalization | 2 | A |
| tests/test_calculations.py | test_blank_currencies_cannot_be_compared | 2 | A |
| tests/test_calculations.py | test_validation_messages_are_exact | 2 | A |
| tests/test_calculations.py | test_reject_nonpositive_or_nonfinite | 1 | A |
| tests/test_calculations.py | test_reject_inverted_discount | 1 | A |
| tests/test_calculations.py | test_discount_rejects_invalid_prices | 1 | A |
| tests/test_calculations.py | test_invalid_pack_counts | 1 | A |
| tests/test_calculations.py | test_invalid_units_and_amounts | 1 | A |
| tests/test_calculations.py | packs | 1 | A |
| tests/test_calculations.py | test_reject_mixed_or_missing_currency | 1 | A |
| tests/test_calculations.py | test_reject_mixed_dimensions_and_single_pack | 1 | A |
| tests/test_calculations.py | test_shrink_rejects_invalid_values | 1 | A |
| tests/test_app.py | test_dashboard_shows_real_coverage_and_every_section | 6 | B |
| tests/test_app.py | test_unit_comparison_flow | 6 | B |
| tests/test_app.py | test_dropdowns_narrow_the_product_list | 5 | A |
| tests/test_app.py | test_offline_food_lookup_flow | 4 | A |
| tests/test_app.py | test_pack_transfer_prefills_unit_comparison | 4 | A |
| tests/test_app.py | test_methods_lists_licences | 4 | A |
| tests/test_app.py | test_user_guide_page_embeds_the_guide | 4 | A |
| tests/test_app.py | button | 3 | A |
| tests/test_app.py | test_changing_the_price_updates_the_verdict | 3 | A |
| tests/test_app.py | test_price_above_mrp_is_rejected_with_a_message | 3 | A |
| tests/test_app.py | test_filter_with_no_match_shows_empty_state | 3 | A |
| tests/test_app.py | test_shrinkflation_case_shows_hidden_increase | 3 | A |
| tests/test_app.py | application | 2 | A |
| tests/test_app.py | html | 2 | A |
| tests/test_app.py | test_pages_render | 2 | A |
| tests/test_app.py | test_unit_comparison_requires_inputs | 2 | A |

## Radon MI

MI is an index, not percent maintainability.

| File | MI | Rank |
| --- | --- | --- |
| src/price_truth/paths.py | 67.73 | A |
| src/price_truth/price_api.py | 42.47 | A |
| src/price_truth/ui.py | 33.21 | A |
| src/price_truth/market_ui.py | 61.42 | A |
| src/price_truth/workspace.py | 16.3 | B |
| src/price_truth/external.py | 38.19 | A |
| src/price_truth/history.py | 44.55 | A |
| src/price_truth/catalogue.py | 51.84 | A |
| src/price_truth/present.py | 41.28 | A |
| src/price_truth/resources.py | 70.78 | A |
| src/price_truth/offers.py | 59.56 | A |
| src/price_truth/dashboard.py | 18.5 | B |
| src/price_truth/calculations.py | 42.83 | A |
| src/price_truth/evidence_store.py | 44.04 | A |
| src/price_truth/model.py | 40.8 | A |
| src/price_truth/theme.py | 39.5 | A |
| src/price_truth/authenticity.py | 49.74 | A |
| src/price_truth/logs.py | 71.03 | A |
| src/price_truth/__init__.py | 100.0 | A |
| src/price_truth/exports.py | 67.51 | A |
| src/price_truth/forecast.py | 46.82 | A |
| src/price_truth/observations.py | 33.08 | A |
| src/price_truth/synthetic.py | 35.58 | A |
| src/price_truth/data.py | 38.17 | A |
| src/price_truth/cache.py | 66.39 | A |
| app.py | 61.66 | A |
| views/methods.py | 76.61 | A |
| views/catalogue.py | 100.0 | A |
| views/dashboard.py | 100.0 | A |
| views/user-guide.py | 85.04 | A |
| views/food.py | 100.0 | A |
| views/observations.py | 100.0 | A |
| scripts/review_current.py | 39.74 | A |
| scripts/build_final_dataset.py | 55.35 | A |
| scripts/model_audit.py | 49.18 | A |
| scripts/uptime_report.py | 77.68 | A |
| scripts/model_development.py | 42.2 | A |
| scripts/review.py | 81.86 | A |
| scripts/browser_current.py | 47.85 | A |
| scripts/concurrency_check.py | 54.66 | A |
| scripts/build_user_guide.py | 51.43 | A |
| scripts/load_test.py | 60.58 | A |
| scripts/data_feasibility.py | 47.58 | A |
| scripts/fetch_real_data.py | 47.48 | A |
| tests/test_data.py | 37.06 | A |
| tests/test_forecast.py | 23.36 | A |
| tests/test_offers.py | 35.02 | A |
| tests/test_price_api.py | 25.12 | A |
| tests/test_services.py | 26.46 | A |
| tests/test_search.py | 33.97 | A |
| tests/test_evidence_store.py | 30.29 | A |
| tests/test_workspace_evidence.py | 30.32 | A |
| tests/test_present.py | 28.54 | A |
| tests/test_observations.py | 24.53 | A |
| tests/test_model.py | 47.63 | A |
| tests/test_logs.py | 51.77 | A |
| tests/test_review_fixes.py | 47.65 | A |
| tests/test_review_fixes_domain.py | 36.82 | A |
| tests/test_synthetic.py | 33.41 | A |
| tests/test_calculations.py | 34.25 | A |
| tests/test_app.py | 35.7 | A |

## Radon raw

| File | LOC | SLOC | Comments |
| --- | --- | --- | --- |
| src/price_truth/paths.py | 10 | 7 | 0 |
| src/price_truth/price_api.py | 106 | 81 | 1 |
| src/price_truth/ui.py | 190 | 160 | 0 |
| src/price_truth/market_ui.py | 59 | 39 | 1 |
| src/price_truth/workspace.py | 481 | 411 | 3 |
| src/price_truth/external.py | 139 | 107 | 1 |
| src/price_truth/history.py | 54 | 42 | 0 |
| src/price_truth/catalogue.py | 38 | 27 | 0 |
| src/price_truth/present.py | 228 | 165 | 1 |
| src/price_truth/resources.py | 69 | 40 | 2 |
| src/price_truth/offers.py | 43 | 34 | 1 |
| src/price_truth/dashboard.py | 396 | 331 | 0 |
| src/price_truth/calculations.py | 59 | 41 | 0 |
| src/price_truth/evidence_store.py | 70 | 57 | 0 |
| src/price_truth/model.py | 216 | 167 | 0 |
| src/price_truth/theme.py | 302 | 236 | 2 |
| src/price_truth/authenticity.py | 153 | 119 | 1 |
| src/price_truth/logs.py | 32 | 22 | 1 |
| src/price_truth/__init__.py | 2 | 0 | 0 |
| src/price_truth/exports.py | 41 | 36 | 1 |
| src/price_truth/forecast.py | 82 | 61 | 1 |
| src/price_truth/observations.py | 134 | 101 | 0 |
| src/price_truth/synthetic.py | 255 | 188 | 1 |
| src/price_truth/data.py | 252 | 199 | 6 |
| src/price_truth/cache.py | 39 | 29 | 1 |
| app.py | 34 | 28 | 0 |
| views/methods.py | 7 | 5 | 0 |
| views/catalogue.py | 5 | 3 | 0 |
| views/dashboard.py | 5 | 3 | 0 |
| views/user-guide.py | 23 | 17 | 2 |
| views/food.py | 4 | 2 | 0 |
| views/observations.py | 4 | 2 | 0 |
| scripts/review_current.py | 178 | 136 | 2 |
| scripts/build_final_dataset.py | 95 | 73 | 1 |
| scripts/model_audit.py | 49 | 41 | 0 |
| scripts/uptime_report.py | 25 | 18 | 2 |
| scripts/model_development.py | 98 | 84 | 0 |
| scripts/review.py | 5 | 3 | 0 |
| scripts/browser_current.py | 152 | 111 | 3 |
| scripts/concurrency_check.py | 68 | 57 | 2 |
| scripts/build_user_guide.py | 286 | 254 | 0 |
| scripts/load_test.py | 79 | 61 | 1 |
| scripts/data_feasibility.py | 52 | 44 | 0 |
| scripts/fetch_real_data.py | 64 | 54 | 0 |
| tests/test_data.py | 138 | 101 | 1 |
| tests/test_forecast.py | 187 | 129 | 0 |
| tests/test_offers.py | 158 | 113 | 0 |
| tests/test_price_api.py | 223 | 154 | 0 |
| tests/test_services.py | 292 | 201 | 1 |
| tests/test_search.py | 179 | 128 | 1 |
| tests/test_evidence_store.py | 151 | 112 | 0 |
| tests/test_workspace_evidence.py | 226 | 166 | 2 |
| tests/test_present.py | 130 | 92 | 0 |
| tests/test_observations.py | 305 | 199 | 0 |
| tests/test_model.py | 76 | 55 | 1 |
| tests/test_logs.py | 30 | 22 | 0 |
| tests/test_review_fixes.py | 79 | 53 | 1 |
| tests/test_review_fixes_domain.py | 173 | 118 | 2 |
| tests/test_synthetic.py | 170 | 117 | 1 |
| tests/test_calculations.py | 180 | 117 | 0 |
| tests/test_app.py | 146 | 95 | 1 |

## Halstead

| File | Volume | Estimated effort |
| --- | --- | --- |
| src/price_truth/paths.py | 59.79 | 39.86 |
| src/price_truth/price_api.py | 402.84 | 1812.79 |
| src/price_truth/ui.py | 345.99 | 1773.18 |
| src/price_truth/market_ui.py | 68.53 | 150.77 |
| src/price_truth/workspace.py | 1452.26 | 11682.53 |
| src/price_truth/external.py | 443.3 | 2544.15 |
| src/price_truth/history.py | 543.93 | 3451.88 |
| src/price_truth/catalogue.py | 113.09 | 339.27 |
| src/price_truth/present.py | 600.41 | 4162.86 |
| src/price_truth/resources.py | 4.75 | 2.38 |
| src/price_truth/offers.py | 147.4 | 620.64 |
| src/price_truth/dashboard.py | 994.33 | 8930.55 |
| src/price_truth/calculations.py | 510.04 | 3559.89 |
| src/price_truth/evidence_store.py | 155.11 | 465.34 |
| src/price_truth/model.py | 561.86 | 4098.3 |
| src/price_truth/theme.py | 361.89 | 1727.21 |
| src/price_truth/authenticity.py | 289.35 | 1302.07 |
| src/price_truth/logs.py | 24.0 | 36.0 |
| src/price_truth/__init__.py | 0 | 0 |
| src/price_truth/exports.py | 72.0 | 280.8 |
| src/price_truth/forecast.py | 452.51 | 3022.09 |
| src/price_truth/observations.py | 410.43 | 1258.06 |
| src/price_truth/synthetic.py | 2711.87 | 31986.13 |
| src/price_truth/data.py | 815.53 | 7998.45 |
| src/price_truth/cache.py | 33.22 | 66.44 |
| app.py | 18.0 | 18.0 |
| views/methods.py | 13.93 | 6.97 |
| views/catalogue.py | 0 | 0 |
| views/dashboard.py | 0 | 0 |
| views/user-guide.py | 22.46 | 22.46 |
| views/food.py | 0 | 0 |
| views/observations.py | 0 | 0 |
| scripts/review_current.py | 621.64 | 2680.81 |
| scripts/build_final_dataset.py | 312.57 | 1209.94 |
| scripts/model_audit.py | 196.73 | 818.4 |
| scripts/uptime_report.py | 87.57 | 175.14 |
| scripts/model_development.py | 235.95 | 884.8 |
| scripts/review.py | 4.75 | 2.38 |
| scripts/browser_current.py | 378.14 | 2079.76 |
| scripts/concurrency_check.py | 193.32 | 869.96 |
| scripts/build_user_guide.py | 55.51 | 83.26 |
| scripts/load_test.py | 116.69 | 330.63 |
| scripts/data_feasibility.py | 240.0 | 886.15 |
| scripts/fetch_real_data.py | 120.4 | 318.72 |
| tests/test_data.py | 928.56 | 5258.11 |
| tests/test_forecast.py | 1525.05 | 5533.92 |
| tests/test_offers.py | 222.94 | 111.47 |
| tests/test_price_api.py | 992.07 | 5396.44 |
| tests/test_services.py | 1646.5 | 10290.63 |
| tests/test_search.py | 779.86 | 2429.57 |
| tests/test_evidence_store.py | 817.84 | 2286.73 |
| tests/test_workspace_evidence.py | 1040.25 | 5898.34 |
| tests/test_present.py | 1425.17 | 9328.37 |
| tests/test_observations.py | 788.34 | 3016.7 |
| tests/test_model.py | 526.0 | 3226.81 |
| tests/test_logs.py | 228.94 | 457.87 |
| tests/test_review_fixes.py | 470.38 | 2351.91 |
| tests/test_review_fixes_domain.py | 1164.13 | 4593.74 |
| tests/test_synthetic.py | 2043.88 | 21072.71 |
| tests/test_calculations.py | 340.49 | 680.99 |
| tests/test_app.py | 826.81 | 4063.34 |

## Local timing

| Measure | Value |
| --- | --- |
| first_assessment_seconds | 0.2217877900000076 |
| warm_calls | 29 |
| warm_p95_seconds | 0.027509026199999197 |
| scope | Sequential local assessment including SHAP; not 100-user load or browser latency |

## Requirements still requiring external evidence

Public deployment/HTTPS, monitored uptime, real-user usability, physical devices and 100-user concurrency are not established by these checks. Browser evidence is recorded separately. Forecasts require sufficient recent comparable observations; controlled test fixtures are not market evaluation.
