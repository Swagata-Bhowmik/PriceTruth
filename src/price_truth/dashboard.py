"""The product dashboard: pick a product with dropdowns, then read every analysis in one full-width grid of cards."""
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
SECTIONS = [("verdict", "Fair price"), ("discount", "Discount check"), ("buy", "Where to buy"),
            ("history", "Price history"), ("packs", "Pack value"), ("shrink", "Shrinkflation"), ("export", "Export")]
DEFAULTS = {"dash_platform": "Amazon", "dash_category": "Electronics"}
CHART = {"displayModeBar": False}


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


def selector(data: pd.DataFrame, columns: list) -> dict | None:
    """Platform → category → subcategory → product, each dropdown narrowing the next, on one row."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
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
        with columns[4]:
            theme.empty_state("No products match these choices",
                              "Clear the name filter or choose All in one of the dropdowns.")
        return None
    labels = dict(zip(matches.key, (product_label(r) for r in matches.itertuples()), strict=True))
    key = columns[4].selectbox(f"Product ({len(matches):,} shown, most-rated first)", list(labels),
                               format_func=labels.get, key="dash_product")
    return matches[matches.key == key].iloc[0].to_dict()


def price_inputs(row: dict, columns: list) -> tuple[float, float]:
    """The listed MRP and the price the shopper sees; both start at today's price for this listing."""
    today_price, today_mrp = current_price(row)
    listed = columns[0].number_input("Listed MRP (₹)", min_value=.01, value=today_mrp, key=f"listed_{row['key']}",
                                     help="The 'was' price the seller shows next to the discount. Starts at today's "
                                          "level for this listing (catalogue price adjusted with official CPI).")
    selling = columns[1].number_input("Price you see (₹)", min_value=.01, value=today_price,
                                      key=f"selling_{row['key']}",
                                      help="Starts at today's price for this listing. Change it to the price you "
                                           "are offered; every card updates.")
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


def verdict_card(row: dict, analysis: dict, selling: float) -> None:
    """Fair-price verdict, range chart and the SHAP explanation."""
    result = analysis["result"]
    theme.card_head("verdict", "Fair price", "Is this price in line?", "gradient boosting + SHAP")
    weak = present.category_quality(REPORTS / "current/model_audit.json", row["platform"], row["category_group"])
    if weak:
        st.warning(f"The model is less reliable for {row['platform'].title()} {row['category_group']} "
                   f"(held-out R² {weak['r2']:.2f}). Treat the verdict as a rough guide.", icon=":material/warning:")
    title, text, tone = present.verdict(present.ASSESSMENT, result["status"])
    theme.verdict(title, text, tone)
    st.plotly_chart(theme.range_chart(result["lower"], result["estimate"], result["upper"], selling),
                    width="stretch", config=CHART, theme=None)
    effects = present.shap_effects(result, row)
    st.plotly_chart(theme.effects_chart(effects["effects"], 300), width="stretch", config=CHART, theme=None)
    st.caption(f"From a typical listing ({present.money(effects['baseline'])}) each factor moved the estimate by the "
               f"percentage shown, reaching {present.money(effects['estimate'])}. {present.basis_note(result)}")


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


def discount_card(row: dict, analysis: dict) -> None:
    """Primary rule on the price history, then the classifier's risk dial and reasons."""
    check, risk = analysis["check"], analysis["risk"]
    theme.card_head("discount", "Discount check", "Is the discount genuine?", "EU 30-day rule + classifier")
    st.markdown("**Primary check: the price-history rule**")
    theme.verdict(*rule_verdict(check))
    columns = st.columns(2)
    columns[0].metric("Usual discount", f"{check['usual_discount_pct']:.0f}%",
                      help="Median discount off MRP over the previous 90 days.")
    columns[1].metric("30-day low", present.money(check["lowest_30d"]),
                      help="Lowest price in the 30 days before the current promotion began. Flagged when the "
                           "discount is 5+ points above usual but the price is less than 5% below this low.")
    st.markdown("**Secondary check: classifier on the listing alone**")
    if risk is None:
        theme.empty_state("Discount model unavailable", "Run scripts/build_final_dataset.py to train it.")
        return
    st.plotly_chart(theme.gauge(risk["probability_inflated"], risk["threshold"]), width="stretch", config=CHART, theme=None)
    effects = present.top_contributions(risk["contributions"], slim(row), top=4)
    st.plotly_chart(theme.contribution_chart(effects, "What raised or lowered the risk", 230), width="stretch",
                    config=CHART, theme=None)
    st.caption("The model sees only the listing (prices, category, platform, rating, whether a sale is on), not the "
               "price history, so when the two checks disagree, trust the rule.")


def offers_chart(offers: pd.DataFrame) -> go.Figure:
    """Total cost per platform, split into price and delivery/fees; hover shows each part."""
    shown = offers[offers.available].iloc[::-1]
    extras = shown.delivery_fee + shown.platform_fee
    figure = go.Figure([
        go.Bar(y=shown.platform, x=shown.price, orientation="h", name="Price", marker_color=theme.PURPLE,
               hovertemplate="%{y}: price ₹%{x:,.0f}<extra></extra>"),
        go.Bar(y=shown.platform, x=extras, orientation="h", name="Delivery + fees", marker_color=theme.PEACH,
               text=[present.money(t) for t in shown.total], textposition="outside", cliponaxis=False,
               hovertemplate="%{y}: delivery and fees ₹%{x:,.0f}<extra></extra>")])
    figure.update_layout(barmode="stack", title="Total cost today, cheapest at the top",
                         legend=dict(orientation="h", y=-0.15), bargap=.35)
    figure.update_xaxes(tickprefix="₹", tickformat=",.0f", range=[0, 1.22 * float(shown.total.max())])
    theme.label_margin(figure, shown.platform.tolist())
    return theme.style_figure(figure, max(260, 46 * len(shown) + 110))


def buy_card(analysis: dict) -> None:
    """Same product across Indian platforms, ranked by total cost including delivery."""
    offers = analysis["offers"]
    theme.card_head("buy", "Where to buy", "Cheapest platform today", "price + delivery + fees")
    if not offers.available.any():
        theme.empty_state("Not available elsewhere today", "No other platform lists this product today.")
        return
    best = offers[offers.available].iloc[0]
    theme.verdict(f"{best.platform}: {present.money(best.total)}", "Lowest total cost including delivery and "
                  "platform fees. Your price is used for this listing's own platform.", "good")
    st.plotly_chart(offers_chart(offers), width="stretch", config=CHART, theme=None)
    table = pd.DataFrame({"Platform": offers.platform, "Total": offers.total, "In stock": offers.available,
                          "Search": offers.link})
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "Total": st.column_config.NumberColumn(format="₹%.0f"),
        "Search": st.column_config.LinkColumn(display_text="Open")})


def history_card(analysis: dict, selling: float) -> None:
    """The 180-day chart with sale periods; hover any day for its price."""
    theme.card_head("history", "Price history", "How the price moved", "last 180 days · sale events shaded")
    st.plotly_chart(history_chart(analysis["history"], selling, 520), width="stretch", config=CHART, theme=None)


def timing_verdict(result: dict) -> None:
    """Buy-timing signal as one compact banner."""
    title, text, tone = present.verdict(present.TIMING, result["status"])
    if "median" in result:
        text = (f"Usual price {present.money(result['median'])}; yours is "
                f"{result['difference_from_median_pct']:+.0f}% against it, over {result['days']} days of history.")
    theme.verdict(title, text, tone)


def timing_card(row: dict, analysis: dict, selling: float) -> None:
    """Position of the price in the last 90 days, the sale calendar and the gated forecast."""
    history = analysis["history"]
    theme.card_head("timing", "Timing", "Buy now or wait?")
    timing_verdict(timing_signal(history[["date", "price"]].iloc[:-1].tail(90), selling))
    if analysis["in_sale"]:
        theme.verdict(f"{history.event.iloc[-1]} is on now", "Today's price is a sale price; check the discount "
                      "card before treating it as a bargain.", "neutral")
    event = synthetic.days_until_next_event(row["platform"])
    if event:
        name, days = event
        theme.verdict(f"Next: {name}", f"Starts {'tomorrow' if days == 1 else f'in {days} days'} on "
                                       f"{row['platform'].title()}.", "muted")
    st.markdown("**Tomorrow's price**")
    show_forecast(forecast_next_day(history[["date", "price"]].tail(120)))


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
def packs_card() -> None:
    """Unit-price comparison; reruns on its own so the product analysis is not recomputed."""
    theme.card_head("packs", "Pack value", "Which pack is better value?", "per 100 g, 100 ml or item")
    if st.session_state.get("prefill_note"):
        st.info(st.session_state["prefill_note"], icon=":material/inventory_2:")
    top = st.columns([1, 1, 1.4])
    currency = top[0].selectbox("Currency", CURRENCIES, key="unit_currency")
    count = top[1].segmented_control("Options", [2, 3, 4], default=2, key="unit_options") or 2
    with st.form("units", border=False):
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
def shrink_card() -> None:
    """Cited and simulated pack reductions, with the hidden unit-price increase."""
    theme.card_head("shrink", "Shrinkflation", "Same price, smaller pack", "10 cited Indian cases + 5 simulated")
    cases = shrink_cases()
    case = st.selectbox("Case", cases, key="shrink_case",
                        format_func=lambda c: f"{c['product']} ({'cited' if c.get('provenance') == 'real' else 'simulated'})")
    points = shrink_points(case)
    first, last = points[0], points[-1]
    change = shrink_change(first["quantity"], last["quantity"], first["price"], last["price"])
    unit = case["unit"]
    theme.verdict(f"{first['quantity']:g}{unit} → {last['quantity']:g}{unit}",
                  f"{change['quantity_reduction_pct']:.0f}% less product, so the real price per {unit} rose "
                  f"{change['unit_price_increase_pct']:.0f}%.", "bad")
    figure = go.Figure(go.Bar(x=[p["period"] for p in points], y=[p["quantity"] for p in points],
                              marker_color=[theme.LAVENDER] + [theme.PEACH] * (len(points) - 1),
                              marker_line_color=[theme.VIOLET] + [theme.CORAL] * (len(points) - 1),
                              marker_line_width=1.5,
                              text=[f"{p['quantity']:g} {unit} · ₹{p['price']:g}" for p in points],
                              textposition="outside", cliponaxis=False,
                              hovertemplate="%{x}: %{y:g} " + unit + "<extra></extra>"))
    figure.update_layout(title="Pack size over time", bargap=.4)
    figure.update_yaxes(ticksuffix=f" {unit}", rangemode="tozero")
    st.plotly_chart(theme.style_figure(figure, 270), width="stretch", config=CHART, theme=None)
    if case.get("source_url"):
        columns = st.columns([2, 1], vertical_alignment="center")
        columns[0].caption(f"Source: {case.get('source_name', 'report')} · {case.get('reported_on', '')}")
        columns[1].link_button("Read the report", case["source_url"], width="stretch")


def export_card(row: dict, analysis: dict, selling: float, listed: float) -> None:
    """Portable copies of the result: PDF report, JSON data, offers CSV and the source listing."""
    result = analysis["result"]
    document = {**result, "listing_key": row["key"], "platform": row["platform"], "quoted_price": selling,
                "listed_price": listed, "currency": "INR", "discount_check": analysis["check"],
                "scope": "historical_price_assessment_not_fraud_verification"}
    head, *buttons = st.columns([1.6, 1, 1, 1, 1], vertical_alignment="center")
    with head:
        theme.card_head("export", "Export", "Keep a copy", "verdict, range, explanation and limits")
    buttons[0].download_button("Download PDF report", lambda: assessment_pdf(row, result, selling, listed),
                               file_name="price_assessment.pdf", mime="application/pdf", on_click="ignore",
                               width="stretch", type="primary")
    buttons[1].download_button("Download data (JSON)", json.dumps(document, indent=2, default=str),
                               file_name="price_assessment.json", mime="application/json", on_click="ignore",
                               width="stretch")
    buttons[2].download_button("Download offers (CSV)", analysis["offers"].to_csv(index=False),
                               file_name="offers.csv", mime="text/csv", on_click="ignore", width="stretch")
    url = safe_url(row["product_url"])
    if url:
        buttons[3].link_button(f"Open on {row['platform'].title()}", url, width="stretch")


def choose(data: pd.DataFrame) -> tuple[dict, float, float] | None:
    """The selector card: four dropdowns, a name filter and the two prices on one row."""
    with st.container(border=True, key="dash_selector"):
        top = st.columns([1, 1.25, 1.4, 1.35], vertical_alignment="bottom")
        bottom = st.columns([3.2, 1, 1], vertical_alignment="bottom")
        row = selector(data, [*top, bottom[0]])
        if row is None:
            return None
        selling, listed = price_inputs(row, bottom[1:])
        product_heading(row)
    return row, selling, listed


def card(name: str):
    """A dashboard card: a bordered container whose key gives it the card styling."""
    return st.container(border=True, key=f"card_{name}")


def grid(row: dict, analysis: dict, selling: float, listed: float) -> None:
    """The cards, laid out to use the full width of the screen."""
    first = st.columns([1.2, 1, 1], gap="medium")
    with first[0], card("verdict"):
        verdict_card(row, analysis, selling)
    with first[1], card("discount"):
        discount_card(row, analysis)
    with first[2], card("buy"):
        buy_card(analysis)
    second = st.columns([1.9, 1], gap="medium")
    with second[0], card("history"):
        history_card(analysis, selling)
    with second[1], card("timing"):
        timing_card(row, analysis, selling)
    third = st.columns(2, gap="medium")
    with third[0], card("packs"):
        packs_card()
    with third[1], card("shrink"):
        shrink_card()
    with card("export"):
        export_card(row, analysis, selling, listed)


def dashboard_page(data: pd.DataFrame, discount_loader=None) -> None:
    """Choose a product once; every analysis is laid out in cards across the full screen."""
    theme.intro("Is this a fair price?",
                "Choose a product and type the price you see. Every card updates: verdict, discount check, cheapest "
                "platform, price history, pack value and shrinkflation.",
                [("listings", f"{len(data):,}"), ("platforms", "8"), ("cited shrink cases", "10")])
    if st.session_state.get("prefill_note"):
        st.info(f"{st.session_state['prefill_note']} [Go to Pack value ↓](#packs)", icon=":material/inventory_2:")
    chosen = choose(data)
    if chosen is None:
        return
    row, selling, listed = chosen
    try:
        analysis = analyse(row, selling, listed, discount_loader() if discount_loader else None)
    except ValueError as exc:
        LOG.warning("assessment rejected", extra={"event": "assessment_rejected", "reason": str(exc)})
        st.error(str(exc))
        return
    theme.kpis(present.kpi_cards(analysis["result"], analysis["check"], analysis["risk"], analysis["offers"],
                                 row["platform"]))
    theme.section_nav(SECTIONS)
    grid(row, analysis, selling, listed)
    theme.footer("Listings are real historical snapshots (Amazon January 2023, Flipkart 2015–16). Daily histories, "
                 "cross-platform offers and discount labels are simulated from them with researched Indian "
                 "e-commerce patterns; see Methods & data. Results describe price position, not seller honesty.")
