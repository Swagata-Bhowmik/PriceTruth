"""Landing page: what Price Truth does and the way into the dashboard."""
from price_truth.landing import landing_page
from price_truth.resources import catalogue, report
from price_truth.ui import shrink_cases

landing_page(len(catalogue()), report("current/model_audit.json"),
             sum(c.get("provenance") == "real" for c in shrink_cases()))
