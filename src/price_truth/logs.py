"""Structured JSON logging: one machine-readable line per event, on standard error."""
import json
import logging
import sys
from datetime import UTC, datetime

# Attributes every LogRecord has; anything else was passed through `extra=` and belongs in the event.
STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Format a record as one JSON object: time, level, logger, message and any `extra` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {"time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
                   "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        payload.update({k: v for k, v in vars(record).items() if k not in STANDARD})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure(level: int = logging.INFO) -> logging.Logger:
    """Attach the JSON handler to the package logger once; repeated calls change nothing."""
    logger = logging.getLogger("price_truth")
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
