"""Health check server utilities."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict, Tuple

HealthCheck = Callable[[], bool]


@dataclass(slots=True)
class HealthMonitor:
    """Registry of health check callbacks."""

    checks: Dict[str, HealthCheck] = field(default_factory=dict)

    def register(self, name: str, check: HealthCheck) -> None:
        self.checks[name] = check

    def status(self) -> Tuple[bool, Dict[str, bool]]:
        results = {name: bool(check()) for name, check in self.checks.items()}
        overall = all(results.values()) if results else True
        return overall, results


@dataclass(slots=True)
class HealthServerConfig:
    host: str = "127.0.0.1"
    port: int = 9001


class HealthCheckServer:
    """Minimal threaded HTTP server exposing health endpoints."""

    def __init__(
        self, monitor: HealthMonitor, config: HealthServerConfig | None = None
    ) -> None:
        self._monitor = monitor
        self._config = config or HealthServerConfig()
        self._thread: threading.Thread | None = None
        self._server: HTTPServer | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        monitor = self._monitor

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - part of BaseHTTPRequestHandler API
                overall, results = monitor.status()
                body = json.dumps(
                    {"status": "ok" if overall else "fail", "checks": results}
                )
                if self.path not in {"/health", "/ready", "/live"}:
                    self.send_response(404)
                    self.end_headers()
                    return

                self.send_response(200 if overall else 503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(
                self, format: str, *args
            ) -> None:  # noqa: A003 - API requirement
                return

        self._server = HTTPServer((self._config.host, self._config.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    @property
    def config(self) -> HealthServerConfig:
        return self._config

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
