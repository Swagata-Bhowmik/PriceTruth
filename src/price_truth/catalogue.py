"""Search and safe exports for historical listings across both platforms."""
from urllib.parse import urlparse

import pandas as pd


def search(frame: pd.DataFrame, query: str, platforms: list[str] | None = None) -> pd.DataFrame:
    """Find literal query words in titles without treating user text as a regex."""
    result = frame
    if platforms is not None:
        result = result[result.platform.isin(platforms)]
    for word in query.strip().split():
        result = result[result.name.str.contains(word, case=False, regex=False, na=False)]
    return result


def safe_url(url: str) -> str | None:
    """Only expose source links to known retail domains; never fetch user URLs."""
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return None
    try:
        parsed = urlparse(url)
        if (parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"www.amazon.in", "www.flipkart.com"}
                or parsed.username or parsed.password):
            return None
    except ValueError:
        return None
    return url


def export_csv(frame: pd.DataFrame) -> bytes:
    """Escape spreadsheet-formula prefixes when exporting external product text."""
    exported = frame.copy()
    for column in exported.select_dtypes(include=["object", "string"]):
        exported[column] = exported[column].map(
            lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
    return exported.to_csv(index=False, lineterminator="\r\n").encode("utf-8-sig")
