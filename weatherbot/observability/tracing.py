"""Simple tracing primitives."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator


@dataclass(slots=True)
class Span:
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    attributes: Dict[str, Any] = field(default_factory=dict)
    end_time: float | None = None
    error: str | None = None

    def finish(self) -> None:
        self.end_time = time.perf_counter()

    @property
    def duration_ms(self) -> float:
        end = self.end_time if self.end_time is not None else time.perf_counter()
        return (end - self.start_time) * 1000

    def to_log_context(self) -> Dict[str, Any]:
        payload = {
            "span": self.name,
            "duration_ms": round(self.duration_ms, 3),
        }
        if self.attributes:
            payload["attributes"] = self.attributes
        if self.error:
            payload["error"] = self.error
        return payload


class Tracer:
    """Utility for emitting span logs."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("weatherbot.tracer")

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        span = Span(name=name, attributes=attributes)
        try:
            yield span
            span.finish()
            self._logger.info("span", extra=span.to_log_context())
        except Exception as exc:  # pragma: no cover - defensive logging
            span.finish()
            span.error = str(exc)
            self._logger.exception("span", extra=span.to_log_context())
            raise

    @asynccontextmanager
    async def async_span(self, name: str, **attributes: Any) -> AsyncIterator[Span]:
        with self.span(name, **attributes) as span:
            yield span


__all__ = ["Tracer", "Span"]
