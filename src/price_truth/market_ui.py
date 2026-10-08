"""Listing price histories and the history chart used by the dashboard (synthetic layer, cached)."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from price_truth import synthetic, theme

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


@st.cache_data(max_entries=256, show_spinner=False)
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
    figure.update_layout(title="Price over the last 180 days", legend=dict(orientation="h", y=-0.2),
                         hovermode="x unified")
    figure.update_xaxes(range=[recent.date.min(), recent.date.max()])
    return theme.style_figure(figure, 360)


def quote_history(history: pd.DataFrame, selling: float, listed: float) -> pd.DataFrame:
    """History with today's simulated offer replaced by the user's quote (same day, same sale event)."""
    frame = history.copy()
    frame.loc[frame.index[-1], ["price", "mrp"]] = [float(selling), float(listed)]
    return frame
