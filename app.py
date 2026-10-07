"""Price Truth Streamlit entrypoint: navigation and shared setup. Pages live in views/."""
import streamlit as st

from price_truth import theme
from price_truth.paths import ROOT
from price_truth.resources import catalogue, start_warmup

st.set_page_config(page_title="Price Truth", page_icon=str(ROOT / "assets/icon.svg"), layout="wide",
                   menu_items={"About": "Price Truth — evidence-based price checks. NMIMS Group 11 academic project."})
theme.apply()
st.logo(str(ROOT / "assets/logo.svg"), size="large", icon_image=str(ROOT / "assets/icon.svg"))

PAGES = {
    "": [st.Page("views/home.py", title="Home", icon=":material/home:", default=True)],
    "Check": [st.Page("views/product.py", title="Price check", icon=":material/fact_check:"),
              st.Page("views/compare.py", title="Unit price", icon=":material/balance:"),
              st.Page("views/food.py", title="Food & packs", icon=":material/barcode_scanner:"),
              st.Page("views/shrink.py", title="Shrinkflation", icon=":material/trending_down:")],
    "Explore": [st.Page("views/observations.py", title="My observations", icon=":material/edit_note:"),
                st.Page("views/catalogue.py", title="Catalogue", icon=":material/storefront:"),
                st.Page("views/methods.py", title="Methods & data", icon=":material/info:")],
    "Help": [st.Page("views/user-guide.py", title="User guide", icon=":material/menu_book:")],
}

page = st.navigation(PAGES)
try:
    catalogue()
    start_warmup()
except FileNotFoundError:
    st.error("The catalogue or model is not prepared. Follow the setup steps in README.md.")
    st.stop()
st.sidebar.caption("Historical prices, real sources. Not live offers or fraud verdicts.")
page.run()
