"""Project paths shared by the command-line tools and interface."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"
REPORTS = ROOT / "reports"
MODEL = ROOT / "artifacts" / "price_model.joblib"

