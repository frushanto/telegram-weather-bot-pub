import asyncio
import logging
from unittest.mock import MagicMock

from weatherbot.core.config import BotConfig
from weatherbot.core.container import Container
from weatherbot.core.events import EventBus, Mediator
from weatherbot.modules.base import ModuleContext, ModuleLoader
from weatherbot.observability.health import HealthMonitor
from weatherbot.observability.metrics import WeatherBotMetrics
from weatherbot.observability.tracing import Tracer


class _LifecycleModule:
    name = "lifecycle"
    order = 0

    def __init__(self, tracker: list[str]) -> None:
        self._tracker = tracker

    def setup(self, context: ModuleContext) -> None:
        context.on_startup(lambda: self._tracker.append("startup"))
        context.on_shutdown(lambda: self._tracker.append("shutdown"))


async def _run_startup(loader: ModuleLoader) -> None:
    await loader.run_startup()


async def _run_shutdown(loader: ModuleLoader) -> None:
    await loader.run_shutdown()


def test_module_loader_runs_lifecycle_hooks() -> None:
    container = Container()
    container.register_singleton(WeatherBotMetrics, WeatherBotMetrics())
    container.register_singleton(Tracer, Tracer(logging.getLogger("test")))
    container.register_singleton(HealthMonitor, HealthMonitor())

    tracker: list[str] = []
    loader = ModuleLoader([_LifecycleModule(tracker)])

    context = ModuleContext(
        application=MagicMock(),
        container=container,
        config=BotConfig(token="token"),
        event_bus=EventBus(),
        mediator=Mediator(),
        _register_startup=loader.register_startup,
        _register_shutdown=loader.register_shutdown,
    )

    loader.setup(context)

    asyncio.run(_run_startup(loader))
    asyncio.run(_run_shutdown(loader))

    assert tracker == ["startup", "shutdown"]
