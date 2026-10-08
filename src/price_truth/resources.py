"""Process-wide cached data and model, plus a background warm-up of SHAP and PDF export."""
import json
import logging
import threading

import streamlit as st

from price_truth.data import load_catalogue
from price_truth.model import load_model
from price_truth.paths import REPORTS

LOG = logging.getLogger(__name__)


@st.cache_data(show_spinner="Loading catalogue…")
def catalogue():
    """Cache read-only catalogue data across reruns and sessions."""
    return load_catalogue()


@st.cache_resource(show_spinner="Loading model…")
def model():
    """Cache the trusted locally generated model across sessions, with category-level training counts."""
    from price_truth.model import with_group_support

    return with_group_support(load_model(), catalogue())


@st.cache_resource(show_spinner="Loading discount model…")
def discount_model():
    """Cache the discount-authenticity classifier; None when it has not been trained."""
    from price_truth.authenticity import MODEL, load

    return load() if MODEL.exists() else None


@st.cache_data
def report(name: str) -> dict | None:
    """Read a saved evaluation report, or None when it is absent."""
    path = REPORTS / name
    return json.loads(path.read_bytes()) if path.exists() else None


@st.cache_data
def json_file(path) -> dict | None:
    """Read any JSON file, or None when it is absent."""
    return json.loads(path.read_bytes()) if path.exists() else None


def _warm(frame, bundle: dict) -> None:
    """Pay one-off SHAP and font-cache costs before the first visitor asks for them."""
    try:
        from price_truth.exports import assessment_pdf
        from price_truth.model import assess

        row = frame.iloc[0].to_dict()
        result = assess(bundle, row, row["selling_price"], row["listed_price"])
        assessment_pdf(row, result, row["selling_price"], row["listed_price"])
    except Exception:  # noqa: BLE001 - warm-up is an optimisation; real calls report their own errors.
        LOG.warning("warm-up skipped", exc_info=True, extra={"event": "warmup_failed"})


@st.cache_resource
def start_warmup() -> threading.Thread:
    """Start the warm-up once per server process."""
    # Load through the shared caches here (main thread) so the warm-up never makes its own copies.
    thread = threading.Thread(target=_warm, args=(catalogue(), model()), name="price-truth-warmup", daemon=True)
    thread.start()
    return thread
