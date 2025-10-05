"""Minimal metrics implementation with Prometheus-compatible exposition."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Iterable, Tuple

LabelKey = Tuple[Tuple[str, str], ...]


def _normalize_labels(labels: Dict[str, str]) -> LabelKey:
    return tuple(sorted(labels.items()))


def _format_labels(key: LabelKey) -> str:
    if not key:
        return ""
    parts = [f'{name}="{value}"' for name, value in key]
    return "{" + ",".join(parts) + "}"


class _BaseMetric:
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self._lock = threading.Lock()

    def help_header(self, metric_type: str) -> Iterable[str]:
        yield f"# HELP {self.name} {self.description}"
        yield f"# TYPE {self.name} {metric_type}"


class CounterMetric(_BaseMetric):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._values: Dict[LabelKey, float] = {}

    def labels(self, **labels: str) -> "CounterHandle":
        return CounterHandle(self, _normalize_labels(labels))

    def _inc(self, key: LabelKey, value: float) -> None:
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def render(self) -> Iterable[str]:
        yield from self.help_header("counter")
        with self._lock:
            for key, value in sorted(self._values.items()):
                yield f"{self.name}{_format_labels(key)} {value}"


class CounterHandle:
    def __init__(self, metric: CounterMetric, key: LabelKey) -> None:
        self._metric = metric
        self._key = key

    def inc(self, amount: float = 1.0) -> None:
        self._metric._inc(self._key, amount)


class GaugeMetric(_BaseMetric):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._values: Dict[LabelKey, float] = {}

    def labels(self, **labels: str) -> "GaugeHandle":
        return GaugeHandle(self, _normalize_labels(labels))

    def _set(self, key: LabelKey, value: float) -> None:
        with self._lock:
            self._values[key] = value

    def _inc(self, key: LabelKey, value: float) -> None:
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def render(self) -> Iterable[str]:
        yield from self.help_header("gauge")
        with self._lock:
            for key, value in sorted(self._values.items()):
                yield f"{self.name}{_format_labels(key)} {value}"


class GaugeHandle:
    def __init__(self, metric: GaugeMetric, key: LabelKey) -> None:
        self._metric = metric
        self._key = key

    def set(self, value: float) -> None:
        self._metric._set(self._key, value)

    def inc(self, amount: float = 1.0) -> None:
        self._metric._inc(self._key, amount)


class SummaryMetric(_BaseMetric):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._values: Dict[LabelKey, Tuple[float, int]] = {}

    def labels(self, **labels: str) -> "SummaryHandle":
        return SummaryHandle(self, _normalize_labels(labels))

    def _observe(self, key: LabelKey, value: float) -> None:
        with self._lock:
            total, count = self._values.get(key, (0.0, 0))
            self._values[key] = (total + value, count + 1)

    def render(self) -> Iterable[str]:
        yield from self.help_header("summary")
        with self._lock:
            for key, (total, count) in sorted(self._values.items()):
                labels = _format_labels(key)
                yield f"{self.name}_sum{labels} {total}"
                yield f"{self.name}_count{labels} {count}"


class SummaryHandle:
    def __init__(self, metric: SummaryMetric, key: LabelKey) -> None:
        self._metric = metric
        self._key = key

    def observe(self, value: float) -> None:
        self._metric._observe(self._key, value)


@dataclass(slots=True)
class MetricsConfig:
    host: str = "127.0.0.1"
    port: int = 9000


class WeatherBotMetrics:
    def __init__(self, config: MetricsConfig | None = None) -> None:
        self._config = config or MetricsConfig()
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.command_total = CounterMetric(
            "weatherbot_command_total",
            "Total number of command executions",
        )
        self.command_failures = CounterMetric(
            "weatherbot_command_failures_total",
            "Total number of failed commands",
        )
        self.event_total = CounterMetric(
            "weatherbot_event_total",
            "Total number of emitted events",
        )
        self._active_subscriptions_metric = GaugeMetric(
            "weatherbot_active_subscription_count",
            "Number of active subscriptions",
        )
        self.active_subscriptions = self._active_subscriptions_metric.labels()
        self.command_latency = SummaryMetric(
            "weatherbot_command_latency_seconds",
            "Summary of command execution latency in seconds",
        )

    def start_server(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        metrics = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path != "/metrics":
                    self.send_response(404)
                    self.end_headers()
                    return

                body = metrics.render().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        self._server = HTTPServer((self._config.host, self._config.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop_server(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    @property
    def config(self) -> MetricsConfig:
        return self._config

    @property
    def server_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def export(self) -> Dict[str, float]:
        return {
            "commands": self.command_total._values.get((), 0.0),
            "command_failures": self.command_failures._values.get((), 0.0),
            "events": self.event_total._values.get((), 0.0),
            "subscriptions": self._active_subscriptions_metric._values.get((), 0.0),
        }

    def render(self) -> str:
        lines: list[str] = []
        lines.extend(self.command_total.render())
        lines.extend(self.command_failures.render())
        lines.extend(self.event_total.render())
        lines.extend(self._active_subscriptions_metric.render())
        lines.extend(self.command_latency.render())
        return "\n".join(lines) + "\n"
