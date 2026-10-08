"""Price Truth Streamlit entrypoint: navigation and shared setup. Pages live in views/."""
import logging

import streamlit as st

from price_truth import logs, theme
from price_truth.paths import ROOT
from price_truth.resources import catalogue, start_warmup

logs.configure()
st.set_page_config(page_title="Price Truth", page_icon=str(ROOT / "assets/icon.svg"), layout="wide",
                   initial_sidebar_state="collapsed",
                   menu_items={"About": "Price Truth — evidence-based price checks. NMIMS Group 11 academic project."})
theme.apply()
st.logo(str(ROOT / "assets/logo.svg"), size="large", icon_image=str(ROOT / "assets/icon.svg"))

PAGES = [
    st.Page("views/dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True),
    st.Page("views/food.py", title="Food & packs", icon=":material/barcode_scanner:"),
    st.Page("views/observations.py", title="My observations", icon=":material/edit_note:"),
    st.Page("views/catalogue.py", title="Catalogue", icon=":material/storefront:"),
    st.Page("views/methods.py", title="Methods & data", icon=":material/info:"),
    st.Page("views/user-guide.py", title="User guide", icon=":material/menu_book:"),
]

page = st.navigation(PAGES, position="top")
try:
    catalogue()
    start_warmup()
except FileNotFoundError:
    logging.getLogger("price_truth.app").error("startup failed", extra={"event": "startup_failed"})
    st.error("The catalogue or model is not prepared. Follow the setup steps in README.md.")
    st.stop()
page.run()
