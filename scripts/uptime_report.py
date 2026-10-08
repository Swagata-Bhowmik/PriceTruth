"""Summarise measured uptime from the scheduled GitHub Actions probe history (needs the gh CLI)."""
import json
import subprocess  # nosec B404 - calls the GitHub CLI with fixed arguments
from datetime import UTC, datetime

from price_truth.paths import REPORTS


def main() -> None:
    """Count successful and failed probes; skipped or cancelled runs are excluded, not counted as up."""
    raw = subprocess.check_output(["gh", "run", "list", "--workflow", "uptime.yml", "--limit", "1000",  # nosec
                                   "--json", "conclusion,createdAt"], text=True)
    runs = [r for r in json.loads(raw) if r["conclusion"] in ("success", "failure")]
    up = sum(r["conclusion"] == "success" for r in runs)
    result = {"generated_at": datetime.now(UTC).isoformat(), "probes": len(runs), "successful": up,
              "uptime_pct": round(100 * up / len(runs), 2) if runs else None,
              "first_probe": min((r["createdAt"] for r in runs), default=None),
              "last_probe": max((r["createdAt"] for r in runs), default=None),
              "scope": "15-minute external health probes from GitHub Actions; scheduling delays leave gaps."}
    (REPORTS / "current" / "uptime.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
