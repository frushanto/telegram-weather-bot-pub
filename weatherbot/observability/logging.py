"""Structured logging utilities for the bot."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Render log records as JSON payloads."""

    #: Attributes provided by :mod:`logging` that should not leak into the payload.
    _RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(
        self, record: logging.LogRecord
    ) -> str:  # noqa: D401 - docstring inherited
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack"] = record.stack_info

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging handler for structured output."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Keep libraries quieter by propagating to the root logger only.
    logging.captureWarnings(True)

    # --- Security: redact Telegram bot token from any logged URLs ---
    class TelegramTokenRedactor(logging.Filter):
        _pattern = re.compile(r"(https://api\.telegram\.org/bot)[^/]+", re.IGNORECASE)

        def filter(self, record: logging.LogRecord) -> bool:
            try:
                # Mask in the message string
                if isinstance(record.msg, str):
                    record.msg = self._pattern.sub(r"\1***REDACTED***", record.msg)
                # Mask in any formatting args (tuple or dict)
                if record.args:

                    def _redact(x):
                        return (
                            self._pattern.sub(r"\1***REDACTED***", x)
                            if isinstance(x, str)
                            else x
                        )

                    if isinstance(record.args, tuple):
                        record.args = tuple(_redact(a) for a in record.args)
                    elif isinstance(record.args, dict):
                        record.args = {k: _redact(v) for k, v in record.args.items()}
            except (
                Exception
            ):  # nosec B110 - intentional broad exception to never break logging
                # Never break logging
                pass
            return True

    # Attach redactor at handler level so it always runs during emission
    handler.addFilter(TelegramTokenRedactor())

    # Reduce noisy HTTP client logs to avoid leaking full URLs via third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
