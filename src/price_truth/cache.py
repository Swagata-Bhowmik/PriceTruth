"""Atomic JSON cache writes and age checks for bounded public API reads."""
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    """Replace the whole cache entry atomically; no half-written records under concurrency."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(value, handle, indent=2)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)


def read_json(path: Path) -> dict | None:
    """Treat malformed local cache data as a miss, never as a successful API response."""
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def fresh(record: dict | None, seconds: int = 3600) -> bool:
    """Only a timezone-aware recent retrieval timestamp can satisfy cache freshness."""
    if not record:
        return False
    try:
        age = (datetime.now(UTC)-datetime.fromisoformat(record["fetched_at"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return False
    return 0 <= age < seconds
