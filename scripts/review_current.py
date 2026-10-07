"""Reproducible review runner with separate collection, measurement and rendering stages."""
import hashlib
import importlib.metadata
import json
import platform
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from price_truth.paths import REPORTS, ROOT

OUT = REPORTS / "current"
TARGETS = ["src", "app.py", "scripts", "tests"]


def mutation_scope() -> list[str]:
    """Read the mutated module list from pyproject.toml so reports never drift from config."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["mutmut"]
    return [path.rsplit("/", 1)[-1] for path in config["source_paths"]]


def execute(args: list[str], filename: str, commands: list) -> str:
    """Write command output and preserve failed exit codes instead of claiming a pass."""
    start = time.perf_counter()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    (OUT / filename).write_text(result.stdout)
    (OUT / (filename + ".stderr")).write_text(result.stderr)
    commands.append({"command": shlex.join(args), "exit_code": result.returncode,
                     "elapsed_seconds": time.perf_counter()-start})
    if result.returncode:
        raise RuntimeError(f"Check failed: {shlex.join(args)}. See {OUT / filename}")
    return result.stdout


def collect_checks(commands: list) -> dict:
    """Run configured lint, behavior tests and each structural metric family."""
    python = sys.executable
    execute([python, "-m", "ruff", "check", *TARGETS, "--output-format", "json"], "ruff.json", commands)
    execute([python, "-m", "pytest", "--cov=price_truth", "--cov-branch",
             f"--cov-report=json:{OUT / 'coverage.json'}", f"--junitxml={OUT / 'pytest.xml'}"],
            "pytest-run.txt", commands)
    metrics = {}
    for kind in ["cc", "mi", "raw", "hal"]:
        metrics[kind] = json.loads(execute([python, "-m", "radon", kind, *TARGETS, "-j"],
                                           f"radon-{kind}.json", commands))
    return metrics


def collect_mutations(commands: list) -> dict:
    """Rerun the mutation scope declared in pyproject.toml; retain every survivor."""
    mutmut = str(Path(sys.executable).with_name("mutmut"))
    execute([mutmut, "run", "price_truth.*"], "mutmut-run.txt", commands)
    execute([mutmut, "results", "--all", "true"], "mutmut-results.txt", commands)
    execute([mutmut, "export-cicd-stats"], "mutmut-export.txt", commands)
    shutil.copyfile(ROOT / "mutants/mutmut-cicd-stats.json", OUT / "mutation.json")
    return json.loads((OUT / "mutation.json").read_text())


def benchmark() -> dict:
    """Measure actual model and SHAP latency separately from browser or concurrent load."""
    from price_truth.data import load_catalogue
    from price_truth.model import assess, load_model
    bundle, data = load_model(), load_catalogue()
    durations = []
    for row in data.groupby("platform").head(15).to_dict("records"):
        start = time.perf_counter()
        assess(bundle, row, row["selling_price"], row["listed_price"])
        durations.append(time.perf_counter()-start)
    return {"first_assessment_seconds": durations[0], "warm_calls": len(durations)-1,
            "warm_p95_seconds": float(np.quantile(durations[1:], .95)),
            "scope": "Sequential local assessment including SHAP; not 100-user load or browser latency"}


def source_manifest(commands: list) -> dict:
    """Bind results to reviewed source bytes, dependency versions and the actual machine."""
    files = [ROOT / "app.py"]
    for directory in ["src", "scripts", "tests"]:
        files.extend(sorted((ROOT / directory).rglob("*.py")))
    packages = ["pandas", "numpy", "scikit-learn", "shap", "streamlit", "pytest", "pytest-cov",
                "ruff", "radon", "mutmut", "reportlab", "requests", "plotly"]
    return {"generated_at": datetime.now(UTC).isoformat(), "python": sys.version,
            "system": platform.platform(), "commands": commands,
            "versions": {p: importlib.metadata.version(p) for p in packages},
            "source_sha256": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            "mutation_scope": mutation_scope()}


def table(headers: list, rows: list) -> str:
    """Format actual evidence, escaping pipes and line breaks inside cells."""
    def line(row):
        return "| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |"
    return "\n".join([line(headers), line(["---"]*len(headers)), *map(line, rows)])


def metrics_sections(metrics: dict) -> list[str]:
    """Present each Radon family separately without conflating index and percentage."""
    cc = [[path, block["name"], block["complexity"], block["rank"]]
          for path, blocks in metrics["cc"].items() for block in blocks]
    mi = [[path, round(v["mi"], 2), v["rank"]] for path, v in metrics["mi"].items()]
    raw = [[path, v["loc"], v["sloc"], v["comments"]] for path, v in metrics["raw"].items()]
    hal = [[path, round(v["total"]["volume"], 2), round(v["total"]["effort"], 2)]
           for path, v in metrics["hal"].items()]
    return ["## Radon CC", table(["File", "Block", "CC", "Rank"], cc),
            "## Radon MI", "MI is an index, not percent maintainability.", table(["File", "MI", "Rank"], mi),
            "## Radon raw", table(["File", "LOC", "SLOC", "Comments"], raw),
            "## Halstead", table(["File", "Volume", "Estimated effort"], hal)]


def render_report(metrics: dict, mutations: dict, timings: dict, manifest: dict) -> str:
    """Render measured results, preserving scope and externally unverified requirements."""
    coverage = json.loads((OUT / "coverage.json").read_text())["totals"]
    suite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    killed, total = mutations["killed"], mutations["total"]
    sections = ["# Price Truth — current engineering review", f"Generated: {manifest['generated_at']}",
                "Historical submission reports are preserved separately; these results apply to this source manifest.",
                "## Ruff", "0 violations under configured rules (command exited successfully).",
                "## PyTest", table(["Measure", "Value"], list(suite.attrib.items())),
                "## Coverage", table(["Measure", "Count", "Percentage"], [
                  ["Statements", f"{coverage['covered_lines']}/{coverage['num_statements']}", f"{100*coverage['covered_lines']/coverage['num_statements']:.2f}%"],
                  ["Branches", f"{coverage['covered_branches']}/{coverage['num_branches']}", f"{100*coverage['covered_branches']/coverage['num_branches']:.2f}%"]]),
                "Coverage scope: price_truth package; scripts and app.py are outside this denominator.",
                "## Mutmut", table(["Outcome", "Count"], list(mutations.items())),
                f"Kill rate: {100*killed/total:.2f}% ({killed}/{total}). Scope: {', '.join(manifest['mutation_scope'])}.",
                "Surviving mutants are justified individually in docs/MUTATION-SURVIVORS.md.",
                *metrics_sections(metrics), "## Local timing", table(["Measure", "Value"], list(timings.items())),
                "## Requirements still requiring external evidence",
                "Public deployment/HTTPS, monitored uptime, real-user usability, physical devices and 100-user concurrency are not established by these checks. Browser evidence is recorded separately. Forecasts require sufficient recent comparable observations; controlled test fixtures are not market evaluation."]
    return "\n\n".join(sections)+"\n"


def main() -> None:
    """Orchestrate separate review stages; write completion metadata only after all pass."""
    OUT.mkdir(parents=True, exist_ok=True)
    commands = []
    metrics = collect_checks(commands)
    mutations = collect_mutations(commands)
    timings = benchmark()
    manifest = source_manifest(commands)
    (OUT / "performance.json").write_text(json.dumps(timings, indent=2))
    (OUT / "review_manifest.json").write_text(json.dumps(manifest, indent=2))
    (OUT / "CODE-REVIEW-REPORT.md").write_text(render_report(metrics, mutations, timings, manifest))
    print(f"Review completed. Evidence: {OUT}")


if __name__ == "__main__":
    main()
