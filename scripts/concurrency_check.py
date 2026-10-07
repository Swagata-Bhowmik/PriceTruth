"""Bounded concurrent model+SHAP benchmark; explicitly not full browser-user capacity."""
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import numpy as np
from threadpoolctl import threadpool_limits

from price_truth.data import load_catalogue
from price_truth.model import assess, load_model
from price_truth.paths import REPORTS


def main() -> None:
    """Release 100 simultaneous warm inference requests and validate every explanation."""
    bundle = load_model()
    rows = load_catalogue().groupby("platform").head(50).to_dict("records")
    assess(bundle, rows[0], rows[0]["selling_price"], rows[0]["listed_price"])
    barrier = threading.Barrier(len(rows), timeout=30)

    def request(row):
        """Synchronize request starts, retain timings and report individual failures."""
        try:
            barrier.wait()
            start = time.perf_counter()
            result = assess(bundle, row, row["selling_price"], row["listed_price"])
            valid = (np.isfinite(result["estimate"]) and result["explanation_error"] < 1e-6
                     and result["lower"] <= result["estimate"] <= result["upper"])
            return {"seconds": time.perf_counter()-start, "ok": bool(valid)}
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}

    start = time.perf_counter()
    with threadpool_limits(limits=1), ThreadPoolExecutor(max_workers=len(rows)) as pool:
        results = list(pool.map(request, rows))
    durations = [r["seconds"] for r in results if "seconds" in r]
    report = {"generated_at": datetime.now(UTC).isoformat(), "concurrent_requests": len(rows),
              "successful": sum(r["ok"] for r in results), "wall_seconds": time.perf_counter()-start,
              "p95_seconds": float(np.quantile(durations, .95)) if durations else None,
              "scope": "100 synchronized in-process warm model+SHAP calls with native thread pools limited to one. Not 100 browser users, external APIs or hosted capacity.",
              "results": results}
    out = REPORTS / "current/concurrency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    assert all(r["ok"] for r in results), "Concurrent calls failed; inspect raw results."


if __name__ == "__main__":
    if os.environ.get("PRICE_TRUTH_LOAD_WORKER") == "1":
        main()
    else:
        environment = {**os.environ, "PRICE_TRUTH_LOAD_WORKER": "1", "OMP_NUM_THREADS": "1",
                       "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"}
        try:
            result = subprocess.run([sys.executable, __file__], env=environment, timeout=120)
            sys.exit(result.returncode)
        except subprocess.TimeoutExpired:
            out = REPORTS / "current/concurrency-timeout.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"status": "timeout", "limit_seconds": 120}))
            sys.exit("Concurrent inference exceeded 120 seconds; no capacity claim.")
