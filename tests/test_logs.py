"""Structured logging: one JSON object per event, configured once."""
import json
import logging

from price_truth import logs


def test_json_formatter_includes_extra_fields_and_exceptions():
    """Fields passed with `extra=` become top-level JSON keys; exceptions are included as text."""
    record = logging.LogRecord("price_truth.x", logging.WARNING, __file__, 1, "assessment %s", ("rejected",), None)
    record.event, record.duration_ms = "assessment_rejected", 12.5
    payload = json.loads(logs.JsonFormatter().format(record))
    assert payload["message"] == "assessment rejected" and payload["level"] == "WARNING"
    assert payload["event"] == "assessment_rejected" and payload["duration_ms"] == 12.5
    assert payload["logger"] == "price_truth.x" and payload["time"].endswith("+00:00")
    try:
        raise ValueError("bad input")
    except ValueError:
        import sys
        record.exc_info = sys.exc_info()
    assert "ValueError: bad input" in json.loads(logs.JsonFormatter().format(record))["exception"]


def test_configure_is_idempotent():
    """Repeated configuration (every Streamlit rerun) never adds duplicate handlers."""
    logger = logs.configure()
    count = len(logger.handlers)
    assert logs.configure() is logger and len(logger.handlers) == count
    assert any(isinstance(h.formatter, logs.JsonFormatter) for h in logger.handlers)
    assert logger.propagate is False and logger.level == logging.INFO
