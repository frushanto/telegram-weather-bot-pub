"""Module configuring logging, metrics and health checks."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass

import httpx

from ..core.events import Event, EventBus
from ..observability.health import HealthCheckServer, HealthMonitor, HealthServerConfig
from ..observability.logging import configure_logging
from ..observability.metrics import MetricsConfig, WeatherBotMetrics
from ..observability.tracing import Tracer
from .base import Module, ModuleContext
from .events import CommandCompleted, CommandFailed, CommandInvoked


@dataclass
class ObservabilityModule(Module):
    name: str = "observability"
    order: int = 0

    def setup(self, context: ModuleContext) -> None:  # noqa: D401
        configure_logging()

        metrics_config = MetricsConfig(
            host=context.config.metrics_host,
            port=context.config.metrics_port,
        )
        metrics = WeatherBotMetrics(metrics_config)
        tracer = Tracer(logging.getLogger("weatherbot.tracer"))

        health_config = HealthServerConfig(
            host=context.config.health_host,
            port=context.config.health_port,
        )
        health_monitor = HealthMonitor()
        health_server = HealthCheckServer(health_monitor, health_config)

        context.container.register_singleton(WeatherBotMetrics, metrics)
        context.container.register_singleton(Tracer, tracer)
        context.container.register_singleton(HealthMonitor, health_monitor)

        def _on_startup() -> None:
            metrics.start_server()
            health_server.start()

        def _on_shutdown() -> None:
            metrics.stop_server()
            health_server.stop()

        context.on_startup(_on_startup)
        context.on_shutdown(_on_shutdown)

        http_client = context.container.get(httpx.AsyncClient)

        async def _close_http_client() -> None:
            close = getattr(http_client, "aclose", None)
            if close is None:
                close = getattr(http_client, "close", None)
            if close is None:
                return
            result = close()
            if inspect.isawaitable(result):
                await result

        context.on_shutdown(_close_http_client)

        event_bus: EventBus = context.event_bus

        async def _record_event(event: Event) -> None:
            metrics.event_total.labels(event=event.name).inc()

        async def _on_command_invoked(event: CommandInvoked) -> None:
            metrics.command_total.labels(command=event.command).inc()

        async def _on_command_failed(event: CommandFailed) -> None:
            metrics.command_failures.labels(command=event.command).inc()

        async def _on_command_completed(event: CommandCompleted) -> None:
            metrics.command_latency.labels(command=event.command).observe(
                event.duration_ms / 1000
            )

        event_bus.subscribe(Event, _record_event)
        event_bus.subscribe(CommandInvoked, _on_command_invoked)
        event_bus.subscribe(CommandFailed, _on_command_failed)
        event_bus.subscribe(CommandCompleted, _on_command_completed)

        health_monitor.register("container", lambda: True)
        health_monitor.register("metrics", lambda: metrics.server_running)
        health_monitor.register("health_server", lambda: health_server.running)
