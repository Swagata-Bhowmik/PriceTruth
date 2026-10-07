"""Methods, data sources, model quality and limits."""
from price_truth.paths import DATA
from price_truth.resources import json_file, report
from price_truth.ui import methods_page

methods_page(report("model_evaluation.json"), report("current/model_audit.json"), report("data_audit.json"),
             json_file(DATA / "final" / "build_summary.json"), report("discount_model_evaluation.json"))
