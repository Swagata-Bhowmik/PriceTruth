"""The single-page product dashboard: pick a product with dropdowns, then scroll through every analysis."""
import json
import logging
import time
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import present, synthetic, theme
from price_truth.authenticity import assess_discount
from price_truth.calculations import compare_packs, shrink_change
from price_truth.catalogue import safe_url
from price_truth.exports import assessment_pdf
from price_truth.forecast import forecast_next_day
from price_truth.history import timing_signal
from price_truth.market_ui import current_price, history_chart, listing_history, quote_history, slim
from price_truth.model import assess
from price_truth.paths import REPORTS
from price_truth.ui import CURRENCIES, UNITS, show_unit_result, shrink_cases, shrink_points
from price_truth.workspace import show_forecast

LOG = logging.getLogger(__name__)
ALL = "All"
SECTIONS = [("verdict", "Fair price"), ("discount", "Discount check"), ("history", "Price history"),
            ("buy", "Where to buy"), ("packs", "Pack value"), ("shrink", "Shrinkflation"), ("export", "Export")]
DEFAULTS = {"dash_platform": "Amazon", "dash_category": "Electronics"}


def options_by_count(frame: pd.DataFrame, column: str) -> list[str]:
    """Distinct values, most common first, so popular choices sit at the top of each dropdown."""
    return frame[column].value_counts().index.tolist()


def narrow(data: pd.DataFrame, platform: str, category: str, subcategory: str, text: str) -> pd.DataFrame:
    """Apply the dropdown choices and the optional name filter; most-rated products first."""
    frame = data if platform == ALL else data[data.platform == platform.lower()]
    frame = frame if category == ALL else frame[frame.category_group == category]
    frame = frame if subcategory == ALL else frame[frame.subcategory.str.split(" > ").str[-1] == subcategory]
    if text.strip():
        frame = frame[frame.name.str.contains(text.strip(), case=False, regex=False)]
    return frame.sort_values("rating_count", ascending=False, na_position="last").head(1500)


def product_label(row) -> str:
    """Dropdown text: platform, shortened name and catalogue price."""
    name = row.name if len(row.name) <= 90 else row.name[:87] + "…"
    return f"{row.platform.title()} · {name} · {present.money(row.selling_price)}"


def selector(data: pd.DataFrame) -> dict | None:
    """Platform → category → subcategory → product, each dropdown narrowing the next."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    columns = st.columns([1, 1.3, 1.6, 1.4], vertical_alignment="bottom")
    platform = columns[0].selectbox("Platform", [ALL, "Amazon", "Flipkart"], key="dash_platform")
    pool = data if platform == ALL else data[data.platform == platform.lower()]
    category = columns[1].selectbox("Category", [ALL, *options_by_count(pool, "category_group")], key="dash_category")
    pool = pool if category == ALL else pool[pool.category_group == category]
    leaves = pool.subcategory.str.split(" > ").str[-1]
    subcategory = columns[2].selectbox("Subcategory", [ALL, *leaves.value_counts().index.tolist()],
                                       key="dash_subcategory")
    text = columns[3].text_input("Filter by name", key="dash_filter", placeholder="e.g. cable, kurta")
    matches = narrow(data, platform, category, subcategory, text)
    if matches.empty:
        theme.empty_state("No products match these choices",
                          "Clear the name filter or choose All in one of the dropdowns.")
        return None
    labels = dict(zip(matches.key, (product_label(r) for r in matches.itertuples()), strict=True))
    key = st.selectbox(f"Product ({len(matches):,} shown, most-rated first)", list(labels),
                       format_func=labels.get, key="dash_product")
    return matches[matches.key == key].iloc[0].to_dict()


def price_inputs(row: dict) -> tuple[float, float]:
    """The listed MRP and the price the shopper sees; both start at today's price for this listing."""
    today_price, today_mrp = current_price(row)
    columns = st.columns([1, 1, 2], vertical_alignment="bottom")
    listed = columns[0].number_input("Listed MRP (₹)", min_value=.01, value=today_mrp, key=f"listed_{row['key']}",
                                     help="The 'was' price the seller shows next to the discount.")
    selling = columns[1].number_input("Price you see (₹)", min_value=.01, value=today_price,
                                      key=f"selling_{row['key']}",
                                      help="Starts at today's price for this listing. Change it to the price you "
                                           "are offered.")
    columns[2].caption("Change either price and every figure below updates. Prices start at today's level for "
                       "this listing (historical catalogue price adjusted with official CPI inflation).")
    return float(selling), float(listed)


@st.cache_data(max_entries=512, show_spinner=False)
def run_assessment(row: dict, selling: float, listed: float) -> dict:
    """Model estimate with SHAP for one quote (cached per product and price)."""
    from price_truth.resources import model

    started = time.perf_counter()
    result = assess(model(), row, selling, listed)
    LOG.info("assessment", extra={"event": "assessment", "platform": row["platform"], "status": result["status"],
                                  "duration_ms": round(1000 * (time.perf_counter() - started), 1)})
    return result


def analyse(row: dict, selling: float, listed: float, discount_bundle: dict | None) -> dict:
    """Every computed result the dashboard shows, from the domain modules."""
    result = run_assessment(row, selling, listed)
    history = listing_history(slim(row), date.today())
    check = synthetic.reference_check(quote_history(history, selling, listed), selling, listed)
    in_sale = bool(history.event.iloc[-1])
    risk = assess_discount(discount_bundle, slim(row), selling, listed, in_sale) if discount_bundle else None
    return {"result": result, "history": history, "check": check, "risk": risk, "in_sale": in_sale,
            "offers": synthetic.offers_with_quote(slim(row), selling)}


def product_heading(row: dict) -> None:
    """Product identity with the source of each part of the analysis."""
    rating = f"★ {row['rating']:.1f} ({int(row['rating_count']):,} ratings)" if pd.notna(row.get("rating")) \
        and pd.notna(row.get("rating_count")) else "No rating recorded"
    observed = str(row.get("observed_at") or "")[:10] or "date unknown"
    theme.product_header(row["name"], [row["platform"].title(), row["category_group"],
                                       str(row["subcategory"]).split(" > ")[-1], row.get("brand") or "",
                                       rating, f"Catalogue {present.money(row['selling_price'])} on {observed}"],
                         [("real", "Listing: real catalogue"), ("sim", "History & offers: simulated")])


def verdict_section(row: dict, analysis: dict, selling: float) -> None:
    """Fair-price verdict, range chart and the SHAP explanation side by side."""
    result = analysis["result"]
    theme.section("verdict", "Fair price", "Is this price in line with similar listings?",
                  "A gradient-boosting model trained on 21k real listings estimates what this product should "
                  "cost. SHAP shows which facts pushed the estimate up or down.")
    weak = present.category_quality(REPORTS / "current/model_audit.json", row["platform"], row["category_group"])
    if weak:
        st.warning(f"The model is less reliable for {row['platform'].title()} {row['category_group']} "
                   f"(held-out R² {weak['r2']:.2f}). Treat the verdict as a rough guide.", icon=":material/warning:")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        title, text, tone = present.verdict(present.ASSESSMENT, result["status"])
        theme.verdict(title, text, tone)
        st.plotly_chart(theme.range_chart(result["lower"], result["estimate"], result["upper"], selling),
                        width="stretch", config={"displayModeBar": False})
        st.caption(f"{present.basis_note(result)} The range is calibrated to hold 90% of held-out selling prices; "
                   "it is not a probability that a discount is genuine.")
    with right:
        effects = present.shap_effects(result, row)
        st.plotly_chart(theme.effects_chart(effects["effects"]), width="stretch", config={"displayModeBar": False})
        st.caption(f"Starting from a typical listing ({present.money(effects['baseline'])}), each factor changed "
                   f"the estimate by the percentage shown, reaching {present.money(effects['estimate'])}.")


def rule_verdict(check: dict) -> tuple[str, str, str]:
    """Plain-language outcome of the 30-day reference-price rule."""
    low = present.money(check["lowest_30d"])
    if check["inflated"]:
        return ("The discount looks inflated",
                f"{check['claimed_discount_pct']:.0f}% off is well above the usual {check['usual_discount_pct']:.0f}%, "
                f"yet the price is not really below its 30-day low of {low}.", "bad")
    if check["real_discount_pct"] >= 5:
        return ("A real price drop", f"The price is {check['real_discount_pct']:.0f}% below its lowest price of the "
                                     f"last 30 days ({low}).", "good")
    position = (f"only {check['real_discount_pct']:.0f}% below" if check["real_discount_pct"] > .5
                else "not below")
    return ("A usual discount, not a special deal",
            f"{check['claimed_discount_pct']:.0f}% off MRP is close to the usual {check['usual_discount_pct']:.0f}%, "
            f"and the price is {position} its 30-day low of {low}.", "neutral")


def discount_section(row: dict, analysis: dict) -> None:
    """Reference-price rule on the left, the classifier's risk and reasons on the right."""
    check, risk = analysis["check"], analysis["risk"]
    theme.section("discount", "Discount check", "Is the discount genuine?",
                  "Two independent checks: the price history against the 30-day lowest price (EU Omnibus rule), "
                  "and a classifier that judges the listing as a shopper sees it.")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.markdown("**Primary check: the price-history rule**")
        theme.verdict(*rule_verdict(check))
        columns = st.columns(2)
        columns[0].metric("Usual discount (90 days)", f"{check['usual_discount_pct']:.0f}%",
                          help="Median discount off MRP over the previous 90 days.")
        columns[1].metric("Lowest price, 30 days", present.money(check["lowest_30d"]),
                          help="Lowest price in the 30 days before the current promotion began.")
        st.caption("Flagged when the advertised discount is at least 5 points above usual but the price is less "
                   "than 5% below the 30-day low.")
    with right:
        st.markdown("**Secondary check: classifier on the listing alone**")
        if risk is None:
            theme.empty_state("Discount model unavailable", "Run scripts/build_final_dataset.py to train it.")
            return
        st.plotly_chart(theme.gauge(risk["probability_inflated"], risk["threshold"]), width="stretch",
                        config={"displayModeBar": False})
        st.caption("Secondary signal. The model sees only the listing (prices, category, platform, rating, whether "
                   "a sale is on), not the price history, so when the two checks disagree, trust the rule.")
    if risk is not None:
        effects = present.top_contributions(risk["contributions"], slim(row))
        st.plotly_chart(theme.contribution_chart(effects, "What raised or lowered the risk"), width="stretch",
                        config={"displayModeBar": False})


def history_section(row: dict, analysis: dict, selling: float) -> None:
    """180-day chart with sale periods, the buy-timing signal, the next sale and the gated forecast."""
    history = analysis["history"]
    theme.section("history", "Price history & timing", "Is now a good time to buy?",
                  "Daily prices for the last 180 days with sale events shaded. Hover over the line for any day's "
                  "price.")
    st.plotly_chart(history_chart(history, selling), width="stretch", config={"displayModeBar": False})
    timing, upcoming, forecast = st.columns(3, gap="medium")
    with timing:
        st.markdown("**Your price vs the last 90 days**")
        timing_card(timing_signal(history[["date", "price"]].iloc[:-1].tail(90), selling))
    with upcoming:
        st.markdown("**Sale calendar**")
        event = synthetic.days_until_next_event(row["platform"])
        if analysis["in_sale"]:
            theme.verdict(f"{history.event.iloc[-1]} is on now", "Today's price is a sale price. Check the "
                          "discount section above before treating it as a bargain.", "neutral")
        if event:
            name, days = event
            theme.verdict(name, f"Starts {'tomorrow' if days == 1 else f'in {days} days'} on "
                                f"{row['platform'].title()}. Sellers sometimes raise prices just before a sale, so "
                                "compare with the 30-day low.", "neutral")
        else:
            theme.empty_state("No sale scheduled", "No upcoming event is on this platform's calendar.")
    with forecast:
        st.markdown("**Tomorrow's price**")
        show_forecast(forecast_next_day(history[["date", "price"]].tail(120)))


def timing_card(result: dict) -> None:
    """Buy-timing signal as one compact banner (the full metrics live on the observations page)."""
    title, text, tone = present.verdict(present.TIMING, result["status"])
    if "median" in result:
        text = (f"Usual price {present.money(result['median'])}; yours is "
                f"{result['difference_from_median_pct']:+.0f}% against it, over {result['days']} days of history.")
    theme.verdict(title, text, tone)


def offers_chart(offers: pd.DataFrame) -> go.Figure:
    """Total cost per platform, split into price and delivery/fees; hover shows each part."""
    shown = offers[offers.available].iloc[::-1]
    extras = shown.delivery_fee + shown.platform_fee
    figure = go.Figure([
        go.Bar(y=shown.platform, x=shown.price, orientation="h", name="Price", marker_color=theme.PURPLE,
               hovertemplate="%{y}: price ₹%{x:,.0f}<extra></extra>"),
        go.Bar(y=shown.platform, x=extras, orientation="h", name="Delivery + fees", marker_color=theme.AMBER,
               text=[present.money(t) for t in shown.total], textposition="outside", cliponaxis=False,
               hovertemplate="%{y}: delivery and fees ₹%{x:,.0f}<extra></extra>")])
    figure.update_layout(barmode="stack", title="Total cost today, cheapest at the top",
                         legend=dict(orientation="h", y=-0.15))
    figure.update_xaxes(tickprefix="₹", tickformat=",.0f", range=[0, 1.18 * float(shown.total.max())])
    return theme.style_figure(figure, max(240, 44 * len(shown) + 110))


def buy_section(row: dict, analysis: dict) -> None:
    """Same product across Indian platforms, ranked by total cost including delivery."""
    offers = analysis["offers"]
    theme.section("buy", "Where to buy", "Which platform is cheapest today?",
                  "Same-product offers on up to eight Indian platforms that sell this category, with real delivery "
                  "thresholds and platform fees.")
    if not offers.available.any():
        theme.empty_state("Not available elsewhere today", "No other platform lists this product today.")
        return
    left, right = st.columns([1.2, 1], gap="medium")
    left.plotly_chart(offers_chart(offers), width="stretch", config={"displayModeBar": False})
    table = pd.DataFrame({"Platform": offers.platform, "Price": offers.price,
                          "Delivery + fees": offers.delivery_fee + offers.platform_fee, "Total": offers.total,
                          "In stock": offers.available, "Search": offers.link})
    right.dataframe(table, hide_index=True, width="stretch", column_config={
        "Price": st.column_config.NumberColumn(format="₹%.0f"),
        "Delivery + fees": st.column_config.NumberColumn(format="₹%.0f"),
        "Total": st.column_config.NumberColumn(format="₹%.0f"),
        "Search": st.column_config.LinkColumn(display_text="Open")})


def pack_row(index: int, currency: str) -> dict:
    """One pack option on a single row; keys match the food page's pre-fill."""
    columns = st.columns([.8, 1.2, 1.2, 1, .8], vertical_alignment="bottom")
    columns[0].markdown(f"**Option {index}**")
    price = columns[1].number_input(f"Price ({currency})", min_value=.01, value=None, key=f"price{index}")
    quantity = columns[2].number_input("Quantity per pack", min_value=.01, value=None, key=f"quantity{index}")
    unit = columns[3].selectbox("Unit", UNITS, key=f"unit{index}")
    packs = columns[4].number_input("Packs", min_value=1, value=1, key=f"count{index}")
    return {"name": f"Option {index}", "price": price, "quantity": quantity, "unit": unit, "packs": packs,
            "currency": currency}


@st.fragment
def packs_section() -> None:
    """Unit-price comparison; reruns on its own so the product analysis above is not recomputed."""
    theme.section("packs", "Pack value", "Which pack size is better value?",
                  "Enter two to four pack options. Prices are normalised to 100 g, 100 ml or one item.")
    if st.session_state.get("prefill_note"):
        st.info(st.session_state["prefill_note"], icon=":material/inventory_2:")
    top = st.columns([1, 1, 3])
    currency = top[0].selectbox("Currency", CURRENCIES, key="unit_currency")
    count = top[1].segmented_control("Options", [2, 3, 4], default=2, key="unit_options") or 2
    with st.form("units"):
        packs = [pack_row(index, currency) for index in range(1, count + 1)]
        submitted = st.form_submit_button("Compare value", type="primary")
    if not submitted:
        return
    if any(p["price"] is None or p["quantity"] is None for p in packs):
        st.error("Enter a price and a quantity for every option.")
        return
    try:
        show_unit_result(compare_packs(packs), currency)
    except ValueError as exc:
        st.error(str(exc))


@st.fragment
def shrink_section() -> None:
    """Cited and simulated pack reductions, with the hidden unit-price increase."""
    theme.section("shrink", "Shrinkflation", "Same price, smaller pack",
                  "Documented Indian cases where the pack shrank while the price stayed the same, and simulated "
                  "multi-step timelines (generic names).")
    cases = shrink_cases()
    left, right = st.columns([1, 1.4], gap="medium")
    with left:
        case = st.selectbox("Case", cases, key="shrink_case",
                            format_func=lambda c: f"{c['product']} ({'cited' if c.get('provenance') == 'real' else 'simulated'})")
        points = shrink_points(case)
        first, last = points[0], points[-1]
        change = shrink_change(first["quantity"], last["quantity"], first["price"], last["price"])
        unit = case["unit"]
        theme.verdict(f"{first['quantity']:g}{unit} → {last['quantity']:g}{unit}",
                      f"{change['quantity_reduction_pct']:.0f}% less product, so the real price per {unit} rose "
                      f"{change['unit_price_increase_pct']:.0f}%.", "bad")
        if case.get("source_url"):
            st.caption(f"Source: {case.get('source_name', 'report')} · {case.get('reported_on', '')}")
            st.link_button("Read the original report", case["source_url"])
    with right:
        figure = go.Figure(go.Bar(x=[p["period"] for p in points], y=[p["quantity"] for p in points],
                                  marker_color=[theme.PURPLE] + [theme.CORAL] * (len(points) - 1),
                                  text=[f"{p['quantity']:g} {unit} · ₹{p['price']:g}" for p in points],
                                  textposition="outside", cliponaxis=False,
                                  hovertemplate="%{x}: %{y:g} " + unit + "<extra></extra>"))
        figure.update_layout(title="Pack size over time")
        figure.update_yaxes(ticksuffix=f" {unit}", rangemode="tozero")
        st.plotly_chart(theme.style_figure(figure, 300), width="stretch", config={"displayModeBar": False})


def export_section(row: dict, analysis: dict, selling: float, listed: float) -> None:
    """Portable copies of the result: PDF report, JSON data, offers CSV and the source listing."""
    theme.section("export", "Export", "Keep a copy",
                  "The PDF and JSON include the quoted prices, the model range, the explanation and the data limits.")
    result = analysis["result"]
    document = {**result, "listing_key": row["key"], "platform": row["platform"], "quoted_price": selling,
                "listed_price": listed, "currency": "INR", "discount_check": analysis["check"],
                "scope": "historical_price_assessment_not_fraud_verification"}
    columns = st.columns(4)
    columns[0].download_button("Download PDF report", lambda: assessment_pdf(row, result, selling, listed),
                               file_name="price_assessment.pdf", mime="application/pdf", on_click="ignore",
                               width="stretch", type="primary")
    columns[1].download_button("Download data (JSON)", json.dumps(document, indent=2, default=str),
                               file_name="price_assessment.json", mime="application/json", on_click="ignore",
                               width="stretch")
    columns[2].download_button("Download offers (CSV)", analysis["offers"].to_csv(index=False),
                               file_name="offers.csv", mime="text/csv", on_click="ignore", width="stretch")
    url = safe_url(row["product_url"])
    if url:
        columns[3].link_button(f"Open on {row['platform'].title()}", url, width="stretch")


def dashboard_page(data: pd.DataFrame, discount_loader=None) -> None:
    """Choose a product once; every analysis follows on one scrolling page."""
    theme.intro("Is this a fair price?",
                "Pick a product, enter the price you see, and scroll through the verdict, the discount check, its "
                "price history and the cheapest place to buy.",
                [("listings", f"{len(data):,}"), ("platforms", "8"), ("cited shrink cases", "10")])
    if st.session_state.get("prefill_note"):
        st.info(f"{st.session_state['prefill_note']} [Go to Pack value ↓](#packs)", icon=":material/inventory_2:")
    with st.container(border=True):
        row = selector(data)
        if row is None:
            return
        selling, listed = price_inputs(row)
    product_heading(row)
    try:
        analysis = analyse(row, selling, listed, discount_loader() if discount_loader else None)
    except ValueError as exc:
        LOG.warning("assessment rejected", extra={"event": "assessment_rejected", "reason": str(exc)})
        st.error(str(exc))
        return
    theme.kpis(present.kpi_cards(analysis["result"], analysis["check"], analysis["risk"], analysis["offers"],
                                 row["platform"]))
    theme.section_nav(SECTIONS)
    verdict_section(row, analysis, selling)
    discount_section(row, analysis)
    history_section(row, analysis, selling)
    buy_section(row, analysis)
    packs_section()
    shrink_section()
    export_section(row, analysis, selling, listed)
    theme.footer("Listings are real historical snapshots (Amazon January 2023, Flipkart 2015–16). Daily histories, "
                 "cross-platform offers and discount labels are simulated from them with researched Indian "
                 "e-commerce patterns; see Methods & data. Results describe price position, not seller honesty.")
