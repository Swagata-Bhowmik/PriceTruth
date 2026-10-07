"""Home: search-first entry, honest coverage numbers and links to each tool."""
import streamlit as st

from price_truth import theme
from price_truth.resources import catalogue, report

theme.hero("Truth. Transparency. Trust.", "Know what a price really means",
           "Check an online discount against what similar products actually sold for, compare pack sizes, "
           "and spot shrinking packs — with the evidence shown every time.")

with st.form("home_search", border=False):
    columns = st.columns([4, 1], vertical_alignment="bottom")
    query = columns[0].text_input("What are you buying?", placeholder="e.g. charging cable, smart watch, jeans")
    if columns[1].form_submit_button("Check price", type="primary", width="stretch"):
        st.session_state["product_query"] = query
        st.switch_page("views/product.py")

data = catalogue()
audit = report("current/model_audit.json")
status = report("current/collection_status.json")
stats = st.columns(4)
theme.stat(stats[0], f"{len(data):,}", "Amazon & Flipkart listings")
theme.stat(stats[1], f"{audit['overall']['median_absolute_percentage_error']:.0f}%" if audit else "—",
           "typical model error on unseen products")
theme.stat(stats[2], f"{status['unique_source_observations']:,}" if status else "—", "dated shop price observations")
theme.stat(stats[3], "8", "shopping platforms compared")

st.space("small")
cards = [
    ("views/product.py", "🎯", "Price check", "Is the discount real? See the expected price range and what drove it."),
    ("views/compare.py", "⚖️", "Unit price", "Which pack is better value per 100 g, 100 ml or item."),
    ("views/food.py", "🔍", "Food & packs", "Look up a barcode, its pack size and dated shop prices."),
    ("views/shrink.py", "📉", "Shrinkflation", "Documented cases of smaller packs at the same price."),
]
for row in (cards[:2], cards[2:]):
    for column, (page, icon, title, text) in zip(st.columns(2), row, strict=True):
        with column.container(border=True):
            st.page_link(page, label=f"**{title}**", icon=icon)
            st.caption(text)

with st.expander("How Price Truth works"):
    st.markdown(
        "1. **Pick a product** from 21k+ real historical listings, or a food barcode.\n"
        "2. **Enter the price you see.** A trained model estimates what similar listings sold for and shows a range.\n"
        "3. **Read the verdict and its reasons.** Every number links back to its source. When the data cannot "
        "support an answer, the app says so instead of guessing.")
st.caption("Academic project · Group 11, NMIMS · Prices are historical snapshots, not live offers. "
           "Results describe price position, not seller honesty.")
