"""Streamlit page bodies. Calculations come from domain modules; this file only presents them."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import present, theme
from price_truth.catalogue import export_csv, search
from price_truth.paths import DATA

PLATFORMS = {"Both": ["amazon", "flipkart"], "Amazon": ["amazon"], "Flipkart": ["flipkart"]}
UNITS = ["g", "kg", "ml", "l", "count"]
CURRENCIES = ["INR", "EUR", "USD", "GBP"]


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
        return json.loads(final.read_bytes())["cases"]
    evidence = json.loads((DATA / "evidence/shrink_cases.json").read_bytes())
    return [{**c, "source_name": evidence["source_name"], "source_url": evidence["source_url"],
             "reported_on": evidence["reported_on"], "provenance": "real"} for c in evidence["cases"]]


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
        st.json(json.loads((DATA / "final" / "assumptions.json").read_bytes()), expanded=False)


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
