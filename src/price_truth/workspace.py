"""Food pack lookup with dated price history, and the user's own observations."""
import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import present, theme
from price_truth.catalogue import export_csv
from price_truth.evidence_store import accumulated_observations
from price_truth.external import cached_products, lookup_product, search_products
from price_truth.forecast import forecast_next_day
from price_truth.history import load_observations, series_for, timing_signal
from price_truth.observations import (
    COLUMNS,
    daily_series,
    pack_changes,
    read_csv,
    validate_observations,
)
from price_truth.offers import compare_observed_offers
from price_truth.paths import DATA, EXTERNAL
from price_truth.price_api import fetch_observations

COMPARE_PAGE = "views/compare.py"
PACK_UNITS = {"g", "kg", "ml", "l", "count"}


def use_pack_for_comparison(product: dict) -> None:
    """Transfer only the structured pack quantity; the price is left for the user to enter."""
    st.session_state["quantity1"] = float(product["product_quantity"])
    st.session_state["unit1"] = product["product_quantity_unit"].lower()
    st.session_state["price1"] = None
    st.session_state["count1"] = 1
    st.session_state["prefill_note"] = (f"Option 1 is pre-filled with {product.get('product_name') or 'the pack'} "
                                        f"({product.get('quantity') or product['product_quantity']}). Add its price.")
    st.session_state["go_compare"] = True


def price_chart(series: pd.DataFrame, currency: str, basis: str) -> go.Figure:
    """Line chart of daily median observed prices."""
    figure = go.Figure(go.Scatter(x=series.date, y=series.price, mode="lines+markers" if len(series) <= 60 else "lines",
                                  line=dict(color=theme.PURPLE, width=2.5), marker=dict(size=7),
                                  hovertemplate=f"%{{x|%d %b %Y}}: {currency} %{{y:,.2f}}<extra></extra>"))
    figure.update_layout(title=f"Observed price ({currency}, per {basis.lower()})")
    figure.update_xaxes(tickformat="%d %b %Y")
    return theme.style_figure(figure, 300)


def show_timing(result: dict, currency: str) -> None:
    """Present the historical-position result in plain language."""
    title, text, tone = present.verdict(present.TIMING, result["status"])
    theme.verdict(title, f"{text} {result['message']}", tone)
    if "median" in result:
        columns = st.columns(3)
        columns[0].metric("Usual (median) price", present.money(result["median"], currency))
        columns[1].metric("Your quote vs median", f"{result['difference_from_median_pct']:+.0f}%")
        columns[2].metric("History covered", f"{result['days']} dates")


def show_forecast(result: dict) -> None:
    """Present a forecast or the reason none is given; details stay in an expander."""
    title, text, tone = present.verdict(present.FORECAST, result["status"])
    theme.verdict(title, text, tone)
    if result.get("next_day_estimate") is not None:
        columns = st.columns(3)
        columns[0].metric(f"Estimate for {result['forecast_date']}", f"{result['next_day_estimate']:,.2f}")
        columns[1].metric("Test error", f"{result['test_mae']:,.2f}")
        columns[2].metric("Last-price error", f"{result['baseline_test_mae']:,.2f}")
    elif result["status"] == "insufficient_history" and "observed_days" in result:
        st.progress(min(result["observed_days"] / 40, 1.0),
                    text=f"{result['observed_days']} of 40 consecutive daily observations")
    with st.expander("Forecast details"):
        st.json(result, expanded=False)


def history_panel(frame: pd.DataFrame, code: str) -> None:
    """Keep barcode, store, currency and recorded basis fixed throughout the analysis."""
    if frame.empty or "product_code" not in frame:
        theme.empty_state("No dated prices yet", "No shop has reported a price for this barcode. "
                          "Add your own receipts under My observations to start a history.")
        return
    eligible = frame[(frame.product_code == code) & frame.location_id.notna() & frame.currency.notna()].copy()
    if eligible.empty:
        theme.empty_state("No dated prices for this barcode",
                          "Open Prices has no shop observation with a store and currency for this product. "
                          "Try refreshing, another barcode, or add your own observations.")
        return
    eligible["price_per"] = eligible.price_per.fillna("UNKNOWN")
    counts = eligible.groupby(["location_id", "currency", "price_per"]).size().sort_values(ascending=False)
    options = list(counts.index)  # longest history first
    names = eligible.dropna(subset=["location_name"]).groupby("location_id").location_name.first().to_dict() \
        if "location_name" in eligible else {}
    store, currency, basis = st.selectbox(
        "Store, currency and price basis", options,
        format_func=lambda v: f"{names.get(v[0], f'Store {v[0]}')} · {v[1]} · per {v[2].lower()} · {counts[v]} prices")
    series = series_for(eligible, code, store, currency, basis)
    if series.empty:
        theme.empty_state("No usable observations", "All rows for this store were duplicates, unproven or future-dated.")
    else:
        st.plotly_chart(price_chart(series, currency, basis), width="stretch", config={"displayModeBar": False})
    evidence = eligible[(eligible.location_id == store) & (eligible.currency == currency)
                        & (eligible.price_per == basis)]
    with st.expander(f"Source observations ({len(evidence)})"):
        st.dataframe(evidence[["date", "price", "currency", "source_url"]], hide_index=True,
                     column_config={"source_url": st.column_config.LinkColumn("Source")})
        st.download_button("Export these observations (CSV)", export_csv(evidence),
                           file_name=f"price_evidence_{code}.csv", mime="text/csv")
    if basis == "UNKNOWN":
        st.warning("The source does not say whether this price is per item or per kilogram, so a quote cannot be "
                   "compared reliably.")
        return
    columns = st.columns([2, 1], vertical_alignment="bottom")
    quote = columns[0].number_input(f"Your current price ({currency}, per {basis.lower()})", min_value=.01, value=None)
    if columns[1].button("Compare with history", width="stretch"):
        if quote is None:
            st.warning("Enter your current price first.")
        else:
            show_timing(timing_signal(series, quote), currency)
    with st.expander("Next-day forecast"):
        st.caption("Only recent, consecutive daily history can be tested. A barcode alone does not prove the pack "
                   "size stayed the same.")
        if st.checkbox("This history is the same pack bought under the same conditions"):
            show_forecast(forecast_next_day(series))


@st.cache_data(ttl=600, show_spinner=False)
def price_collection() -> tuple[pd.DataFrame, str, bool]:
    """Most complete saved Open Prices collection, a description, and whether the archive was unreadable."""
    latest = EXTERNAL / "current/open_prices_inr.json"
    if latest.exists():
        snapshot = json.loads(latest.read_bytes())
        frame, metadata = pd.DataFrame(snapshot["observations"]), snapshot
    else:
        frame, metadata = load_observations()
    note, archive_failed = f"Saved collection fetched {metadata['fetched_at'][:10]}", False
    archive = EXTERNAL / "archive"
    if archive.exists():
        try:
            accumulated, collection = accumulated_observations(archive)
            if not accumulated.empty:
                frame = accumulated
                note = (f"{collection['unique_source_observations']} observations from "
                        f"{collection['snapshots']} collection runs · latest {collection['latest_retrieval'][:10]}")
        except ValueError:
            archive_failed = True
    simulated = dataset_food_prices()
    if not simulated.empty:
        frame = pd.concat([frame.assign(provenance="real"), simulated], ignore_index=True)
        note += f" · {simulated.product_code.nunique()} products with daily store histories"
    return frame, note, archive_failed


@st.cache_data(show_spinner=False)
def dataset_food_prices() -> pd.DataFrame:
    """Synthetic daily store histories from the finalized dataset (real rows come from the archive)."""
    path = DATA / "final" / "food_prices.csv.gz"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype={"product_code": str, "id": str, "proof_id": str, "price_per": str,
                                     "duplicate_of": object, "source_url": object}, low_memory=False)
    return frame[frame.provenance == "synthetic"].dropna(axis=1, how="all")


def dataset_food_products() -> list[dict]:
    """Products that have daily histories in the dataset, as lookup candidates."""
    frame = dataset_food_prices()
    if frame.empty:
        return []
    names = frame.drop_duplicates("product_code")
    return [{"code": r.product_code, "product_name": r.product_name, "countries": "India"}
            for r in names.itertuples()]


def find_food(offline: bool) -> None:
    """Search by name or barcode and remember the candidates."""
    with st.form("workspace_food_search", border=False):
        columns = st.columns([3, 1], vertical_alignment="bottom")
        query = columns[0].text_input("Food name or barcode", placeholder="e.g. Maggi, or 8–14 digit barcode")
        submitted = columns[1].form_submit_button("Search", type="primary", width="stretch")
    if not submitted:
        return
    try:
        if query.strip().isdigit():
            st.session_state["workspace_food_candidates"] = [lookup_product(query.strip(), offline)["product"]]
        else:
            st.session_state["workspace_food_candidates"] = search_products(query, offline)["products"]
        st.session_state.pop("workspace_price_result", None)
    except ValueError as exc:
        st.error(str(exc))


def pack_details(code: str, offline: bool) -> None:
    """Show the selected pack's details with their source and offer the unit comparison."""
    try:
        result = lookup_product(code, offline)
    except ValueError as exc:
        theme.empty_state("Pack details unavailable", f"{exc} Saved examples work offline.")
        return
    details = result["product"]
    countries = details.get("countries") or ""
    theme.product_card(details.get("product_name") or "Unnamed product",
                       [("Brand", ", ".join(details["brands"]) if isinstance(details.get("brands"), list)
                         else details.get("brands")), ("Pack size", details.get("quantity")),
                        ("Barcode", code), ("Sold in", countries[:60])],
                       "live" if result["mode"] == "live" else "cached",
                       f"Open Food Facts · {result['fetched_at'][:10]}")
    if details.get("categories"):
        st.caption(f"Categories: {details['categories']}")
    quantity = pd.to_numeric(details.get("product_quantity"), errors="coerce")
    unit = str(details.get("product_quantity_unit", "")).lower()
    if pd.notna(quantity) and 0 < quantity < 1e12 and unit in PACK_UNITS:
        st.button("Compare this pack's value", on_click=use_pack_for_comparison, args=(details,), type="primary")
    else:
        st.caption("No structured pack size is recorded, so it cannot be sent to the unit comparison.")
    st.link_button("View source record", result["source_url"])


def food_page() -> None:
    """Pick one barcode and carry it through pack details and dated shop prices."""
    if st.session_state.pop("go_compare", False):
        st.switch_page(COMPARE_PAGE)
    theme.page_header("Food & packs", "Look up a food pack",
                      "Find a product by name or barcode, check its pack size and see what shops charged on which dates.")
    offline = st.toggle("Saved responses only (works offline)", value=False, key="food_offline")
    find_food(offline)
    if "workspace_food_candidates" in st.session_state:
        products = st.session_state["workspace_food_candidates"]  # may be empty: the search found nothing
    else:
        products = cached_products() + dataset_food_products()
    # Named products sold in India first; unnamed saved records stay available at the end.
    with_history = {p["code"] for p in dataset_food_products()}
    products = sorted({p["code"]: p for p in products if p.get("code")}.values(),
                      key=lambda p: (p["code"] not in with_history, not p.get("product_name"),
                                     "India" not in str(p.get("countries", ""))))
    if not products:
        theme.empty_state("No matching products", "Try another name, or paste a barcode from the pack.")
        return
    product = st.selectbox("Product", products, key="food_product",
                           format_func=lambda p: f"{p.get('product_name') or 'Unnamed'} · {p.get('code')}")
    code = str(product["code"])
    tabs = st.tabs(["Pack details", "Price history", "Long-history example"])
    with tabs[0]:
        pack_details(code, offline)
        st.caption("Food barcodes are never matched automatically to Amazon or Flipkart listings.")
    with tabs[1]:
        price_history_tab(code, offline)
    with tabs[2]:
        history_example()


def price_history_tab(code: str, offline: bool) -> None:
    """Saved or refreshed Open Prices observations for one barcode."""
    frame, note, archive_failed = price_collection()
    if archive_failed:
        st.warning("The cumulative archive could not be read; using the dated snapshot instead.")
    columns = st.columns([3, 1], vertical_alignment="center")
    columns[0].caption(f"Open Prices (ODbL) · {note}")
    if columns[1].button("Refresh prices", disabled=offline, width="stretch"):
        try:
            st.session_state["workspace_price_result"] = {"code": code, "result": fetch_observations(code)}
        except ValueError as exc:
            st.error(str(exc))
    saved = st.session_state.get("workspace_price_result", {})
    if saved.get("code") == code:
        result = saved["result"]
        frame = pd.DataFrame(result["observations"])
        st.caption(f"{result['notice']} Fetched {result['fetched_at'][:16]}.")
        if not result["complete_query"]:
            st.warning("Showing at most 100 observations; this history is partial.")
    history_panel(frame, code)


def history_example() -> None:
    """A real, longer EUR store history that demonstrates the history tools; not Indian prices."""
    try:
        frame, metadata = load_observations(True)
    except FileNotFoundError:
        theme.empty_state("Example not downloaded", "Run scripts/fetch_real_data.py to save the example collection.")
        return
    theme.source_badge("cached", f"Open Prices · {metadata['fetched_at'][:10]}")
    st.caption("Real observations from a French store in EUR, included because Indian histories are still short. "
               "It does not represent Indian prices.")
    shops = frame[frame.product_code.notna() & (frame.location_type == "shop")].copy()
    if shops.empty:
        theme.empty_state("No store observations", "The saved example contains no identified shop prices.")
        return
    shops["label"] = shops.product_name.fillna(shops.product_code) + " · " + shops.product_code
    label = st.selectbox("Example product", shops.groupby("label").size().sort_values(ascending=False).index.tolist())
    product = shops[shops.label == label]
    location = product.location_id.iloc[0]
    basis = product[product.location_id == location].price_per.fillna("UNKNOWN").iloc[0]
    code, currency = product.iloc[0]["product_code"], product.iloc[0]["currency"]
    series = series_for(frame, code, location, currency, basis)
    st.plotly_chart(price_chart(series, currency, basis), width="stretch", config={"displayModeBar": False})
    columns = st.columns([2, 1], vertical_alignment="bottom")
    quote = columns[0].number_input(f"Try a quote ({currency})", min_value=.01, value=None, key="example_quote")
    if columns[1].button("Compare", key="example_compare", width="stretch") and quote is not None:
        show_timing(timing_signal(series, quote), currency)


def observations_page() -> None:
    """The user's own dated observations: entry, import, history, store comparison, pack changes."""
    theme.page_header("My observations", "Track prices you have seen",
                      "Add receipts or prices you saw in shops. They stay in this browser session, are never used for "
                      "training, and you can download or clear them at any time.")
    data = st.session_state.get("observations")
    tabs = st.tabs(["Add or import", "Price history", "Compare stores", "Pack changes"])
    with tabs[0]:
        if flash := st.session_state.pop("obs_flash", None):
            st.success(flash)
        add_or_import(data)
    if data is None:
        for tab in tabs[1:]:
            with tab:
                theme.empty_state("No observations yet",
                                  "Upload real dated observations or add one in the first tab to analyse them here.")
        return
    with tabs[1]:
        selected = choose_identity(data, ["product_id", "variant", "store", "currency"], "obs")
        observation_history(selected)
    with tabs[2]:
        offers_panel(data)
    with tabs[3]:
        selected = choose_identity(data, ["product_id", "variant", "store", "currency"], "pack")
        pack_change_panel(selected)


def add_or_import(data: pd.DataFrame | None) -> None:
    """Manual entry, CSV import, template, export and clear."""
    with st.expander("Add one observation", expanded=data is None):
        observation_form()
    upload = st.file_uploader("Or import a CSV (UTF-8, up to 2 MB)", type=["csv"])
    if upload is not None and st.button("Validate and replace my observations"):
        try:
            validated = read_csv(upload.getvalue())
            st.session_state["observations"] = validated
            st.session_state["obs_flash"] = (f"Imported {len(validated)} observations. "
                                             "They are your entries, not independently verified.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    columns = st.columns(3)
    columns[0].download_button("CSV template", ",".join(COLUMNS) + "\n", file_name="observations_template.csv",
                               mime="text/csv", width="stretch")
    if data is None:
        st.info("Upload real dated observations or add one above to start.", icon="📝")
        return
    columns[1].download_button("Save my observations", export_csv(data[COLUMNS]), file_name="my_observations.csv",
                               mime="text/csv", width="stretch")
    if columns[2].button("Clear session observations", width="stretch"):
        del st.session_state["observations"]
        st.rerun()
    theme.source_badge("user", f"{len(data)} observation{'s' if len(data) != 1 else ''}")
    st.dataframe(data[COLUMNS], hide_index=True, column_config={"source_url": st.column_config.LinkColumn("Source")})


def choose_identity(frame: pd.DataFrame, columns: list[str], prefix: str) -> pd.DataFrame:
    """Narrow step by step to one product, variant, store and currency."""
    selected = frame
    layout = st.columns(len(columns))
    for slot, column in zip(layout, columns, strict=True):
        value = slot.selectbox(column.replace("_", " ").capitalize(), selected[column].unique(),
                               key=f"{prefix}_{column}")
        selected = selected[selected[column] == value]
    return selected


def observation_history(selected: pd.DataFrame) -> None:
    """Daily price history and the forecast gate for one exact pack."""
    sizes = list(selected[["quantity", "unit"]].drop_duplicates().itertuples(index=False, name=None))
    size = st.selectbox("Exact pack", sizes, format_func=lambda s: f"{s[0]:g} {s[1]}")
    series = daily_series(selected[(selected.quantity == size[0]) & (selected.unit == size[1])])
    currency = selected.currency.iloc[0]
    st.plotly_chart(price_chart(series, currency, f"{size[0]:g} {size[1]} pack"), width="stretch",
                    config={"displayModeBar": False})
    result = forecast_next_day(series)
    st.subheader("Next-day forecast")
    show_forecast(result)
    st.download_button("Download forecast assessment", json.dumps(result, indent=2),
                       file_name="forecast_assessment.json", mime="application/json")


def pack_change_panel(selected: pd.DataFrame) -> None:
    """Detect pack-size reductions for one confirmed variant over time."""
    confirmed = st.checkbox("These records track the same variant over time, not different packs sold together")
    if not st.button("Analyse pack-size changes", type="primary"):
        return
    try:
        changes = pack_changes(selected, confirmed)
    except ValueError as exc:
        st.error(str(exc))
        return
    if changes.empty:
        theme.empty_state("No change to analyse", "At least two distinct observation dates are needed.")
        return
    st.dataframe(changes, hide_index=True, column_config={
        "from_date": "From", "to_date": "To",
        "quantity_reduction_pct": st.column_config.NumberColumn("Pack smaller by", format="%.1f%%"),
        "unit_price_increase_pct": st.column_config.NumberColumn("Unit price up by", format="%.1f%%"),
        "new_unit_price": st.column_config.NumberColumn("New price per unit", format="%.2f"),
        "before_source": st.column_config.LinkColumn("Before (source)"),
        "after_source": st.column_config.LinkColumn("After (source)")})
    figure = go.Figure([go.Bar(name="Quantity reduction", x=changes.to_date, y=changes.quantity_reduction_pct,
                               marker_color=theme.PURPLE),
                        go.Bar(name="Unit-price increase", x=changes.to_date, y=changes.unit_price_increase_pct,
                               marker_color=theme.CORAL)])
    figure.update_layout(title="Pack changes", barmode="group")
    figure.update_yaxes(ticksuffix="%")
    st.plotly_chart(theme.style_figure(figure, 300), width="stretch", config={"displayModeBar": False})
    st.download_button("Export pack changes", export_csv(changes), file_name="pack_changes.csv", mime="text/csv")


def offers_panel(frame: pd.DataFrame) -> None:
    """Rank recent quotes for one identical pack across stores."""
    st.caption("Uses only quotes dated today or yesterday. Each total must include the same taxes, delivery and "
               "membership conditions.")
    selected = choose_identity(frame, ["product_id", "variant", "currency"], "offer")
    confirmed = st.checkbox("These are identical packs under the same purchase conditions", key="offers_confirmed")
    if not st.button("Compare sourced store quotes", type="primary"):
        return
    try:
        result = compare_observed_offers(selected, confirmed)
    except ValueError as exc:
        st.warning(str(exc))
        return
    best = result.iloc[0]
    theme.verdict(f"Cheapest: {best.store}", f"{present.money(best.price, best.currency)} on {best.date}. "
                  "This is the lowest of your quotes, not a guarantee of the lowest market price.", "good")
    st.dataframe(result, hide_index=True, column_config={"source_url": st.column_config.LinkColumn("Source")})
    st.download_button("Export quote comparison", export_csv(result), file_name="store_quotes.csv", mime="text/csv")


def observation_form() -> None:
    """A dated, source-backed manual quote with the same validation as CSV imports."""
    with st.form("manual_observation"):
        record = {}
        columns = st.columns(2)
        for index, (column, label) in enumerate([("product_id", "Stable product ID or barcode"),
                                                 ("name", "Product name"), ("variant", "Variant (flavour/model)"),
                                                 ("store", "Store / retailer")]):
            record[column] = columns[index % 2].text_input(label, key=f"manual_{column}")
        columns = st.columns(3)
        record["currency"] = columns[0].selectbox("Quote currency", ["INR", "EUR", "USD", "GBP"])
        record["date"] = columns[1].date_input("Observation date", value=date.today(),
                                               max_value=date.today()).isoformat()
        record["price"] = columns[2].number_input("Total price paid", min_value=.01, value=None)
        columns = st.columns(2)
        record["quantity"] = columns[0].number_input("Total quantity purchased", min_value=.01, value=None)
        record["unit"] = columns[1].selectbox("Quantity unit", ["g", "kg", "ml", "l", "count"])
        record["source_url"] = st.text_input("HTTPS source / evidence link",
                                             help="A link to the shop page, receipt photo or other evidence.")
        submitted = st.form_submit_button("Add to my session observations", type="primary")
    if submitted:
        previous = st.session_state.get("observations", pd.DataFrame(columns=COLUMNS))
        try:
            incoming = validate_observations(pd.DataFrame([record]))
            combined = incoming if previous.empty else pd.concat([previous, incoming], ignore_index=True)
            st.session_state["observations"] = validate_observations(combined)
            st.session_state["obs_flash"] = "Observation added. Download your observations to keep them."
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
