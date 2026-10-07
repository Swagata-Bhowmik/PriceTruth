"""Streamlit page bodies. Calculations come from domain modules; this file only presents them."""
import hashlib
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import present, theme
from price_truth.calculations import compare_packs, shrink_change
from price_truth.catalogue import export_csv, safe_url, search
from price_truth.exports import assessment_pdf
from price_truth.model import assess
from price_truth.paths import DATA, REPORTS

PLATFORMS = {"Both": ["amazon", "flipkart"], "Amazon": ["amazon"], "Flipkart": ["flipkart"]}
UNITS = ["g", "kg", "ml", "l", "count"]
CURRENCIES = ["INR", "EUR", "USD", "GBP"]


def listing_picker(data: pd.DataFrame) -> dict | None:
    """Search both catalogues and pick one listing from a selectable results table."""
    columns = st.columns([3, 2], vertical_alignment="bottom")
    query = columns[0].text_input("Search historical listings", key="product_query",
                                  placeholder="e.g. charging cable, smart watch, kurta")
    platform = columns[1].segmented_control("Platform", list(PLATFORMS), default="Both", key="product_platform")
    matches = search(data, query, PLATFORMS[platform or "Both"]).head(200)
    if matches.empty:
        theme.empty_state("No listings match that search",
                          "Try fewer or more general words, or switch the platform filter to Both.")
        return None
    table = pd.DataFrame({"Platform": matches.platform.str.title(), "Product": matches.name,
                          "Variant": matches.variant, "Listed": matches.listed_price,
                          "Sold at": matches.selling_price, "Discount": matches.discount_pct,
                          "ID": matches.product_id})
    st.caption(f"{len(matches):,} listing{'s' if len(matches) != 1 else ''} shown · prices as recorded on the "
               "catalogue date · click a row to choose")
    # A new search gets a new widget key, so a selection never points into a different result set.
    results_id = hashlib.sha256("|".join(matches.key).encode()).hexdigest()[:12]
    event = st.dataframe(table, hide_index=True, on_select="rerun", selection_mode="single-row",
                         key=f"product_table_{results_id}", height=230, column_config={
                             "Listed": st.column_config.NumberColumn(format="₹%.0f"),
                             "Sold at": st.column_config.NumberColumn(format="₹%.0f"),
                             "Discount": st.column_config.NumberColumn(format="%.0f%%"),
                             "Product": st.column_config.TextColumn(width="large"),
                             "Variant": st.column_config.TextColumn(width="medium")})
    rows = event.selection.rows if event and event.selection else []
    index = rows[0] if rows and rows[0] < len(matches) else 0
    return matches.iloc[index].to_dict()


def product_page(data: pd.DataFrame, model_loader, discount_loader=None) -> None:
    """Primary journey: choose a listing, enter a price, see a verdict with its reasons."""
    theme.page_header("Price check", "Is this a good price?",
                      "Compare a price with what similar Amazon and Flipkart listings actually sold for.")
    row = listing_picker(data)
    if row is None:
        return
    theme.product_card(row["name"], [("Platform", row["platform"].title()), ("Category", row["category_group"]),
                                     ("Variant", row.get("variant") or ""), ("ID", row["product_id"]),
                                     ("Currency", "INR"), ("Observed", str(row.get("observed_at") or "")[:10] or "date unknown")],
                       "historical", "not a live offer")
    weak = present.category_quality(REPORTS / "current/model_audit.json", row["platform"], row["category_group"])
    if weak:
        st.warning(f"The model is less reliable for {row['platform'].title()} {row['category_group']} "
                   f"(held-out R² {weak['r2']:.2f}, typical error {weak['median_absolute_percentage_error']:.0f}%). "
                   "Treat the verdict as a rough guide.", icon="⚠️")
    assessment_panel(row, model_loader(), discount_loader() if discount_loader else None)


def assessment_panel(row: dict, bundle: dict, discount_bundle: dict | None = None) -> None:
    """Assess the selected listing; results persist across reruns until the inputs change."""
    from price_truth.market_ui import current_price

    today_price, today_mrp = current_price(row)
    with st.form(f"quote_{row['key']}", border=False):
        columns = st.columns(2)
        listed = columns[0].number_input("Listed (MRP) price, ₹", min_value=.01, value=today_mrp,
                                         help="The 'was' or reference price the seller shows.")
        selling = columns[1].number_input("Price you were offered, ₹", min_value=.01, value=today_price,
                                          help="Starts at today's price for this listing; change it to the "
                                               "price you see.")
        if st.form_submit_button("Check this price", type="primary"):
            st.session_state["price_check"] = {"key": row["key"], "selling": selling, "listed": listed}
    saved = st.session_state.get("price_check")
    if not saved or saved["key"] != row["key"]:
        return
    selling, listed = saved["selling"], saved["listed"]
    try:
        result = assess(bundle, row, selling, listed)
    except ValueError as exc:
        st.error(str(exc))
        return
    show_assessment(row, result, selling, listed)
    from price_truth.market_ui import market_tabs

    market_tabs(row, selling, listed, discount_bundle)


def show_assessment(row: dict, result: dict, selling: float, listed: float) -> None:
    """Verdict, range, reasons and exports for the price-position model."""
    title, text, tone = present.verdict(present.ASSESSMENT, result["status"])
    theme.verdict(title, text, tone)
    columns = st.columns(3)
    columns[0].metric("Advertised discount", f"{result['claimed_discount_pct']:.0f}%")
    columns[1].metric("Model estimate", present.money(result["estimate"]))
    columns[2].metric("Expected range", f"{present.money(result['lower'])}–{present.money(result['upper'])}")
    st.plotly_chart(theme.range_chart(result["lower"], result["estimate"], result["upper"], selling),
                    width="stretch", config={"displayModeBar": False})
    effects = present.shap_effects(result, row)
    st.plotly_chart(theme.effects_chart(effects["effects"]), width="stretch", config={"displayModeBar": False})
    st.caption(f"Starting from a typical listing ({present.money(effects['baseline'])}), each factor raised or "
               f"lowered the estimate by the percentage shown, reaching {present.money(effects['estimate'])}. "
               "These are computed SHAP contributions of the trained model. They explain the estimate, "
               "not whether a seller is honest.")
    with st.expander("How to read this result"):
        st.markdown(
            f"- **Comparable listings:** {result['support']} training listings share this platform and subcategory.\n"
            "- **Expected range:** calibrated to contain 90% of held-out selling prices for comparable data. "
            "It is not a 90% probability that a discount is real.\n"
            "- **Listed price matters:** the model uses the listed price, so an inflated MRP can raise the estimate.\n"
            "- **Historical data:** Flipkart listings are from 2015–2016; Amazon dates are unknown.")
        if result["seen_in_training"]:
            st.caption("This listing was part of training. Published accuracy uses separate held-out products.")
        st.caption(f"Technical: log-space prediction {result['prediction_log']:.4f}, "
                   f"baseline {result['base_log']:.4f}, explanation error {result['explanation_error']:.2e}.")
    document = {**result, "listing_key": row["key"], "platform": row["platform"],
                "quoted_price": selling, "listed_price": listed, "currency": "INR",
                "scope": "historical_price_assessment_not_fraud_verification"}
    columns = st.columns(3)
    columns[0].download_button("Download PDF report", lambda: assessment_pdf(row, result, selling, listed),
                               file_name="price_assessment.pdf", mime="application/pdf", on_click="ignore",
                               width="stretch")
    columns[1].download_button("Download data (JSON)", json.dumps(document, indent=2),
                               file_name="price_assessment.json", mime="application/json", on_click="ignore",
                               width="stretch")
    url = safe_url(row["product_url"])
    if url:
        columns[2].link_button(f"Open on {row['platform'].title()}", url, width="stretch")


def pack_inputs(index: int, currency: str) -> dict:
    """One pack option; keys are stable so other pages can pre-fill a pack."""
    with st.container(border=True):
        st.markdown(f"**Option {index}**")
        price = st.number_input(f"Price ({currency})", min_value=.01, value=None, key=f"price{index}")
        quantity = st.number_input("Quantity per pack", min_value=.01, value=None, key=f"quantity{index}")
        columns = st.columns(2)
        unit = columns[0].selectbox("Unit", UNITS, key=f"unit{index}")
        count = columns[1].number_input("Packs", min_value=1, value=1, key=f"count{index}")
    return {"name": f"Option {index}", "price": price, "quantity": quantity, "unit": unit,
            "packs": count, "currency": currency}


def unit_page() -> None:
    """Compare two to four pack options of one product on price per 100 g/ml or per item."""
    theme.page_header("Unit price", "Which pack is better value?",
                      "Enter the price and size of each option. Prices are normalised to 100 g, 100 ml or one item.")
    if st.session_state.get("prefill_note"):
        st.info(st.session_state["prefill_note"], icon="📦")
    top = st.columns([1, 1, 2])
    currency = top[0].selectbox("Currency", CURRENCIES, key="unit_currency")
    options = top[1].segmented_control("Options", [2, 3, 4], default=2, key="unit_options") or 2
    with st.form("units", border=False):
        columns = st.columns(options)
        packs = []
        for index, column in enumerate(columns, 1):
            with column:
                packs.append(pack_inputs(index, currency))
        submitted = st.form_submit_button("Compare value", type="primary")
    if not submitted:
        return
    if any(p["price"] is None or p["quantity"] is None for p in packs):
        st.error("Enter a price and a quantity for every option.")
        return
    try:
        result = compare_packs(packs)
    except ValueError as exc:
        st.error(str(exc))
        return
    show_unit_result(result, currency)


def show_unit_result(result: list[dict], currency: str) -> None:
    """Best-value verdict, unit-price chart and ranked table for compared packs."""
    best, worst = result[0], result[-1]
    if abs(best["value"] - worst["value"]) < 1e-9:
        theme.verdict("Same value", "Every option costs the same per unit.", "neutral")
    else:
        saving = 100 * (1 - best["value"] / worst["value"])
        theme.verdict(f"{best['name']} is the best value",
                      f"{present.money(best['value'], currency)} per {best['basis']}, "
                      f"{saving:.0f}% cheaper per unit than {worst['name']}.", "good")
    figure = go.Figure(go.Bar(x=[r["name"] for r in result], y=[r["value"] for r in result],
                              marker_color=[theme.MINT] + [theme.PURPLE] * (len(result) - 1),
                              text=[present.money(r["value"], currency) for r in result], textposition="outside",
                              cliponaxis=False))
    figure.update_layout(title=f"Price per {best['basis']} (lower is better)")
    st.plotly_chart(theme.style_figure(figure, 300), width="stretch", config={"displayModeBar": False})
    table = pd.DataFrame([{"Rank": i, "Option": r["name"], f"Per {r['basis']}": round(r["value"], 2),
                           "Pack price": r["price"], "Quantity": f"{r['packs']} × {r['quantity']:g} {r['unit']}"}
                          for i, r in enumerate(result, 1)])
    st.dataframe(table, hide_index=True)
    st.caption("A lower unit price across different sizes is not a lower price for the same exact pack. "
               "Inputs are your own quotes and are not stored.")


def shrink_points(case: dict) -> list[dict]:
    """Normalise a two-point reported case or a multi-step timeline into dated points."""
    if "timeline" in case:
        return case["timeline"]
    return [{"period": case["old_period"], "quantity": case["old_quantity"], "price": case["old_price"]},
            {"period": case["new_period"], "quantity": case["new_quantity"], "price": case["new_price"]}]


def shrink_cases() -> list[dict]:
    """Cases from the finalized dataset, falling back to the original cited evidence."""
    final = DATA / "final" / "shrink_cases.json"
    if final.exists():
        return json.loads(final.read_text())["cases"]
    evidence = json.loads((DATA / "evidence/shrink_cases.json").read_text())
    return [{**c, "source_name": evidence["source_name"], "source_url": evidence["source_url"],
             "reported_on": evidence["reported_on"], "provenance": "real"} for c in evidence["cases"]]


def shrink_page() -> None:
    """Pack reductions at the same or similar price, with the hidden unit-price increase."""
    theme.page_header("Shrinkflation", "Same price, smaller pack",
                      "Cases where the pack got smaller while the price stayed about the same.")
    cases = shrink_cases()
    case = st.selectbox("Product", cases, key="shrink_case", format_func=lambda c: c["product"])
    points = shrink_points(case)
    first, last = points[0], points[-1]
    result = shrink_change(first["quantity"], last["quantity"], first["price"], last["price"])
    unit = case["unit"]
    theme.verdict(f"{first['quantity']:g}{unit} → {last['quantity']:g}{unit}"
                  f"{' at ₹' + format(last['price'], 'g') if first['price'] == last['price'] else ''}",
                  f"You get {result['quantity_reduction_pct']:.0f}% less, so the real price per {unit} rose "
                  f"{result['unit_price_increase_pct']:.0f}%.", "bad")
    columns = st.columns(3)
    columns[0].metric("Quantity reduction", f"{result['quantity_reduction_pct']:.1f}%")
    columns[1].metric("Hidden price increase", f"{result['unit_price_increase_pct']:.1f}%")
    columns[2].metric("Label price", f"₹{first['price']:g} → ₹{last['price']:g}")
    figure = go.Figure(go.Bar(x=[p["period"] for p in points], y=[p["quantity"] for p in points],
                              marker_color=[theme.PURPLE] + [theme.CORAL] * (len(points) - 1),
                              text=[f"{p['quantity']:g} {unit} · ₹{p['price']:g}" for p in points],
                              textposition="outside", cliponaxis=False))
    figure.update_layout(title="Pack size over time")
    figure.update_yaxes(ticksuffix=f" {unit}", rangemode="tozero")
    st.plotly_chart(theme.style_figure(figure, 320), width="stretch", config={"displayModeBar": False})
    if case.get("notes"):
        st.markdown(f"**About this case.** {case['notes']}")
    if case.get("source_url"):
        st.caption(f"{case.get('source_name', 'Source')} · {case.get('reported_on', '')}")
        st.link_button("Read the original report", case["source_url"])
    st.caption("To track your own packs over time, add dated observations under My observations and use "
               "Analyse pack-size changes.")


def catalogue_page(data: pd.DataFrame) -> None:
    """Browse and export both historical catalogues without implying cross-platform matches."""
    theme.page_header("Catalogue", "Browse historical listings",
                      "Search 21k+ Amazon and Flipkart listings. Similar names may be different products or variants.")
    columns = st.columns([3, 2], vertical_alignment="bottom")
    query = columns[0].text_input("Search product names", key="catalogue_query")
    platform = columns[1].segmented_control("Platform", list(PLATFORMS), default="Both", key="catalogue_platform")
    result = search(data, query, PLATFORMS[platform or "Both"])
    theme.source_badge("historical", "INR · not live offers")
    if result.empty:
        theme.empty_state("No listings found", "Try fewer words or a broader product name.")
        return
    shown = result[["platform", "name", "listed_price", "selling_price", "discount_pct", "observed_at"]]
    st.caption(f"{len(result):,} matches · showing up to 500")
    st.dataframe(shown.head(500), hide_index=True, column_config={
        "platform": "Platform", "name": st.column_config.TextColumn("Product", width="large"),
        "listed_price": st.column_config.NumberColumn("Listed", format="₹%.0f"),
        "selling_price": st.column_config.NumberColumn("Sold at", format="₹%.0f"),
        "discount_pct": st.column_config.NumberColumn("Discount", format="%.0f%%"),
        "observed_at": "Observed"})
    st.download_button("Download results (CSV)", export_csv(shown), file_name="historical_catalogue_results.csv",
                       mime="text/csv")


def dataset_tab(summary: dict | None, discount: dict | None) -> None:
    """Composition of the finalized dataset by provenance, and the discount model's evaluation."""
    if not summary:
        theme.empty_state("Dataset not built", "Run scripts/build_final_dataset.py to generate the final dataset.")
        return
    rows = [["Marketplace listings (Amazon Jan 2023, Flipkart 2015–16)", f"{summary['real_listings']:,}", "Real"],
            ["Daily price histories", f"{summary['price_history']['rows']:,} days · "
             f"{summary['price_history']['products']} products", "Synthetic"],
            ["Labelled offers for the discount model", f"{summary['discount_training']['rows']:,}", "Synthetic"],
            ["Cross-platform offers", f"{summary['offers']['rows']:,}", "Synthetic"]]
    rows += [[f"Food shop prices ({k})", f"{v:,}", k.title()] for k, v in summary["food_prices"].items()]
    rows += [[f"Shrinkflation cases ({k})", str(v), k.title()] for k, v in summary["shrink_cases"].items()]
    st.dataframe(pd.DataFrame(rows, columns=["Table", "Rows", "Provenance"]), hide_index=True)
    st.markdown(
        "Synthetic layers are generated by a seeded simulator (`synthetic.py`) calibrated to researched Indian "
        "e-commerce patterns — sale calendars, category discount depths, price-revision frequency, pre-sale price "
        "rises and platform delivery fees. Each product's history is anchored to its real catalogue price, "
        "adjusted to May 2025 price levels with official MoSPI CPI indices. "
        "Every synthetic row carries `provenance = synthetic` in the dataset files and exports. "
        "The price model is trained and evaluated on real listings only.")
    if discount:
        test = discount["test"]
        columns = st.columns(4)
        columns[0].metric("Discount model ROC AUC", f"{test['roc_auc']:.2f}")
        columns[1].metric("Precision", f"{test['precision']:.0%}")
        columns[2].metric("Recall", f"{test['recall']:.0%}")
        columns[3].metric("Test offers", f"{test['n']:,}")
        st.caption(f"{discount['selected_model'].replace('_', ' ').title()} evaluated on products it never saw, "
                   f"using synthetic labels. {discount['label_rule']}")
    with st.expander("Generator assumptions and sources"):
        st.json(json.loads((DATA / "final" / "assumptions.json").read_text()), expanded=False)


def methods_page(evaluation: dict | None, audit: dict | None, data_audit: dict | None,
                 summary: dict | None = None, discount: dict | None = None) -> None:
    """Explain data, model quality, limits and licences, using saved real reports."""
    theme.page_header("About", "Methods, data and limits",
                      "How Price Truth reaches its results, how accurate it is, and what it cannot tell you.")
    if audit:
        overall = audit["overall"]
        columns = st.columns(4)
        columns[0].metric("Held-out listings", f"{audit['held_out_rows']:,}")
        columns[1].metric("Typical error", f"{overall['median_absolute_percentage_error']:.0f}%",
                          help="Median absolute percentage error on products never seen in training.")
        columns[2].metric("Mean absolute error", present.money(overall["mae_inr"]))
        columns[3].metric("R²", f"{overall['r2']:.3f}")
    tabs = st.tabs(["Model quality", "Dataset", "Data sources & licences", "What this cannot do", "Raw reports"])
    with tabs[0]:
        st.markdown("The model is a histogram gradient-boosting regressor predicting **log(1 + selling price)** "
                    "from listed price, rating, rating count, platform and category. It was chosen over a baseline "
                    "and a random forest on validation error. Related titles are grouped before splitting to reduce "
                    "leakage. Explanations use SHAP TreeExplainer on the fitted model.")
        if audit:
            groups = pd.DataFrame(audit["subgroups"])
            groups["platform"] = groups.platform.str.title()
            groups["Reliability"] = groups.r2.map(lambda r: "Weak" if r < .5 else "Moderate" if r < .8 else "Good")
            st.dataframe(groups[["platform", "category", "n", "median_absolute_percentage_error", "r2", "Reliability"]],
                         hide_index=True, column_config={
                             "platform": "Platform", "category": "Category", "n": "Listings",
                             "median_absolute_percentage_error": st.column_config.NumberColumn("Typical error",
                                                                                               format="%.0f%%"),
                             "r2": st.column_config.NumberColumn("R²", format="%.2f")})
            st.caption("Held-out subgroups with at least 30 listings. Weak categories show a warning on the price check.")
    with tabs[1]:
        dataset_tab(summary, discount)
    with tabs[2]:
        st.dataframe(pd.DataFrame([
            ["Amazon Sales Dataset (Kaggle, Karkavelraja J)", "1,347 listings after cleaning", "CC BY-NC-SA 4.0"],
            ["Flipkart Products (Kaggle, PromptCloud)", "19,920 listings, 2015–2016", "CC BY-SA 4.0"],
            ["Open Food Facts", "Barcode pack details, live and saved", "ODbL 1.0"],
            ["Open Prices (Open Food Facts)", "Dated shop price observations", "ODbL 1.0"],
            ["Bloomberg via Financial Express, 13 May 2022", "Two reported pack reductions", "Cited, not redistributed"],
        ], columns=["Source", "Used for", "Licence"]), hide_index=True)
        st.caption("Datasets are used for non-commercial academic purposes with attribution. Derived data keeps the "
                   "same licences. No retailer websites are scraped.")
    with tabs[3]:
        st.markdown("- **Not a legal finding about a seller.** Discount checks apply a reference-price rule and a "
                    "model trained on simulated, research-calibrated price histories. They show what such a check "
                    "would conclude, not proof of dishonesty.\n"
                    "- **Catalogue prices are historical** (Amazon January 2023, Flipkart 2015–16). Daily histories, "
                    "cross-platform offers and most food shop prices are simulated from those anchors; the Dataset "
                    "tab lists exactly which tables are real and which are synthetic.\n"
                    "- **Forecasts are gated.** A next-day estimate is shown only when it beats simply repeating the "
                    "last price on held-out days.\n"
                    "- **No automatic product matching** between food barcodes and marketplace listings.\n"
                    "- **Your entries stay in your session** and are never used for training. Download a CSV to keep them.")
    with tabs[4]:
        for name, payload in [("Dataset audit", data_audit), ("Model evaluation", evaluation), ("Model audit", audit)]:
            if payload:
                with st.expander(name):
                    st.json(payload, expanded=False)
