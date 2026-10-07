"""Price-check result tabs built on the dataset's price histories, offers and discount model."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import present, synthetic, theme
from price_truth.authenticity import assess_discount
from price_truth.forecast import forecast_next_day
from price_truth.history import timing_signal
from price_truth.workspace import show_forecast, show_timing

LISTING_FIELDS = ["key", "platform", "category_group", "listed_price", "selling_price", "name", "rating",
                  "rating_count", "observed_at"]


@st.cache_data(max_entries=256, show_spinner=False)
def listing_history(listing: dict, end: date) -> pd.DataFrame:
    """Cached daily history for one listing."""
    return synthetic.price_history(listing, end)


def current_price(row: dict) -> tuple[float, float]:
    """Today's selling price and shown MRP for a listing."""
    latest = listing_history(slim(row), date.today()).iloc[-1]
    return float(latest.price), float(latest.mrp)


def slim(row: dict) -> dict:
    """Only the fields the generators need, so caching keys stay small."""
    return {k: row.get(k) for k in LISTING_FIELDS}


def history_chart(history: pd.DataFrame, quote: float) -> go.Figure:
    """Last 180 days of price and shown MRP, sale periods shaded, with the user's quote."""
    recent = history.tail(180)
    figure = go.Figure()
    for _, block in recent[recent.event != ""].groupby((recent.event != recent.event.shift()).cumsum()):
        figure.add_vrect(x0=block.date.min(), x1=block.date.max(), fillcolor=theme.MINT, opacity=.12, line_width=0,
                         annotation_text=block.event.iloc[0], annotation_position="top left",
                         annotation_font_size=11)
    # A far-above MRP line would flatten the price line; start it hidden (one click on the legend shows it).
    mrp_visible = True if recent.mrp.median() <= 2 * recent.price.median() else "legendonly"
    figure.add_trace(go.Scatter(x=recent.date, y=recent.mrp, name="Listed (MRP)", mode="lines",
                                line=dict(color="#B9B3CC", dash="dot"), visible=mrp_visible))
    figure.add_trace(go.Scatter(x=recent.date, y=recent.price, name="Selling price", mode="lines",
                                line=dict(color=theme.PURPLE, width=2.5)))
    figure.add_hline(y=quote, line_color=theme.CORAL, line_dash="dash", annotation_text="Your price",
                     annotation_position="bottom right")
    figure.update_yaxes(tickprefix="₹", tickformat=",.0f")
    figure.update_layout(title="Price over the last 180 days", legend=dict(orientation="h", y=-0.2))
    return theme.style_figure(figure, 360)


def quote_history(history: pd.DataFrame, selling: float, listed: float) -> pd.DataFrame:
    """History with today's simulated offer replaced by the user's quote (same day, same sale event)."""
    frame = history.copy()
    frame.loc[frame.index[-1], ["price", "mrp"]] = [float(selling), float(listed)]
    return frame


def authenticity_tab(row: dict, history: pd.DataFrame, selling: float, listed: float, bundle: dict | None) -> None:
    """30-day lowest-price rule on the history, then the classifier's probability and reasons."""
    check = synthetic.reference_check(quote_history(history, selling, listed), selling, listed)
    if check["inflated"]:
        theme.verdict("The discount looks inflated",
                      f"{check['claimed_discount_pct']:.0f}% off is advertised, well above this product's usual "
                      f"{check['usual_discount_pct']:.0f}%, yet the price is not really lower than its 30-day low of "
                      f"{present.money(check['lowest_30d'])}.", "bad")
    elif check["real_discount_pct"] >= 5:
        theme.verdict("A real price drop",
                      f"The price is {check['real_discount_pct']:.0f}% below its lowest price of the last 30 days "
                      f"({present.money(check['lowest_30d'])}).", "good")
    else:
        theme.verdict("A usual discount, not a special deal",
                      f"{check['claimed_discount_pct']:.0f}% off MRP is close to this product's usual "
                      f"{check['usual_discount_pct']:.0f}%. The price is not below its 30-day low of "
                      f"{present.money(check['lowest_30d'])}.", "neutral")
    columns = st.columns(4)
    columns[0].metric("Advertised discount", f"{check['claimed_discount_pct']:.0f}%")
    columns[1].metric("Usual discount (90 days)", f"{check['usual_discount_pct']:.0f}%")
    columns[2].metric("Lowest price, 30 days", present.money(check["lowest_30d"]))
    columns[3].metric("Real saving vs 30-day low", f"{check['real_discount_pct']:.0f}%")
    st.caption("Rule: a discount is flagged when it is advertised as at least 5 points bigger than usual but the "
               "price is less than 5% below its lowest price in the 30 days before the promotion began (the EU Omnibus reference-price "
               "principle, adapted to MRP-based listings).")
    if bundle is None:
        return
    in_sale = bool(history.event.iloc[-1])
    model = assess_discount(bundle, row, selling, listed, in_sale)
    probability = model["probability_inflated"]
    st.subheader("Model estimate")
    st.progress(probability, text=f"{probability:.0%} estimated risk that this discount is inflated, judged from "
                                  f"the listing alone ({'flagged' if model['flagged'] else 'below the flag threshold'} "
                                  f"of {model['threshold']:.0%})")
    effects = present.top_contributions(model["contributions"], row)
    st.plotly_chart(theme.contribution_chart(effects, "What raised or lowered the risk"), width="stretch",
                    config={"displayModeBar": False})
    st.caption("The classifier sees only what a shopper sees (prices, discount, category, platform, rating, "
               "whether a sale is on). It does not see the price history used for the rule above.")


def timing_tab(row: dict, history: pd.DataFrame, quote: float) -> None:
    """History chart, position of the quote, next sale event and the gated forecast."""
    st.plotly_chart(history_chart(history, quote), width="stretch", config={"displayModeBar": False})
    series = history[["date", "price"]].iloc[:-1].tail(90)
    show_timing(timing_signal(series, quote), "INR")
    upcoming = synthetic.days_until_next_event(row["platform"])
    if upcoming:
        name, days = upcoming
        when = "tomorrow" if days == 1 else f"in {days} days"
        st.info(f"Next sale on {row['platform'].title()}: **{name}** starts {when}. Sellers sometimes raise prices "
                "just before a sale, so compare with the 30-day low.", icon="📅")
    st.subheader("Tomorrow's price")
    show_forecast(forecast_next_day(history[["date", "price"]].tail(120)))


def offers_tab(row: dict) -> None:
    """Same-product offers across platforms, ranked by total cost including delivery."""
    offers = synthetic.offers_for(row)
    available = offers[offers.available]
    if available.empty:
        theme.empty_state("Not available elsewhere today", "No other platform lists this product today.")
        return
    best = available.iloc[0]
    own = offers[offers.platform.str.lower() == row["platform"]]
    saving = float(own.total.iloc[0] - best.total) if not own.empty else 0.0
    if best.platform.lower() == row["platform"] or saving <= 0:
        theme.verdict(f"Best price is on {best.platform}", f"{present.money(best.total)} including delivery.", "good")
    else:
        theme.verdict(f"Cheaper on {best.platform}",
                      f"{present.money(best.total)} including delivery — {present.money(saving)} less than "
                      f"{row['platform'].title()}.", "good")
    for offer in offers.itertuples():
        with st.container(border=True):
            columns = st.columns([2, 2, 2, 2], vertical_alignment="center")
            columns[0].markdown(f"**{offer.platform}**")
            columns[1].markdown(present.money(offer.price) if offer.available else "Out of stock")
            extras = offer.delivery_fee + offer.platform_fee
            columns[2].caption("Free delivery" if extras == 0 else f"{present.money(extras)} delivery and fees")
            columns[3].link_button("Search", offer.link, width="stretch", disabled=not offer.available)
    st.download_button("Download offers (CSV)", offers.to_csv(index=False), file_name="offers.csv", mime="text/csv")


def market_tabs(row: dict, selling: float, listed: float, discount_bundle: dict | None) -> None:
    """Discount check, history and timing, and where to buy for the selected listing."""
    history = listing_history(slim(row), date.today())
    tabs = st.tabs(["Discount check", "Price history & timing", "Where to buy"])
    with tabs[0]:
        authenticity_tab(slim(row), history, selling, listed, discount_bundle)
    with tabs[1]:
        timing_tab(row, history, selling)
    with tabs[2]:
        offers_tab(slim(row))
    st.caption("How these figures are produced is explained under Methods & data.")
