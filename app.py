"""Price Truth Streamlit entrypoint: navigation and shared setup. Pages live in views/."""
import logging
import sys
from pathlib import Path

import streamlit as st

# Hosts such as Streamlit Community Cloud install requirements.txt but not this package itself;
# importing straight from src/ works there, in Docker and in an editable local install alike.
SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from price_truth import logs, theme  # noqa: E402
from price_truth.paths import ROOT  # noqa: E402
from price_truth.resources import catalogue, start_warmup  # noqa: E402

logs.configure()
st.set_page_config(page_title="Price Truth", page_icon=str(ROOT / "assets/icon.svg"), layout="wide",
                   initial_sidebar_state="collapsed",
                   menu_items={"About": "Price Truth — evidence-based price checks. NMIMS Group 11 academic project."})
theme.apply()
st.logo(str(ROOT / "assets/logo.svg"), size="large", icon_image=str(ROOT / "assets/icon.svg"))

PAGES = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/dashboard.py", title="Dashboard", icon=":material/space_dashboard:"),
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
