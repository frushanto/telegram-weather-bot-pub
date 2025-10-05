"""Core abstractions for modular bot composition."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, List, Protocol

from telegram.ext import Application

from ..core.config import BotConfig
from ..core.container import Container
from ..core.events import EventBus, Mediator
from ..observability.health import HealthMonitor
from ..observability.metrics import WeatherBotMetrics
from ..observability.tracing import Tracer

LifecycleHook = Callable[[], Awaitable[None] | None]


@dataclass
class ModuleContext:
    application: Application
    container: Container
    config: BotConfig
    event_bus: EventBus
    mediator: Mediator
    _register_startup: Callable[[LifecycleHook], None]
    _register_shutdown: Callable[[LifecycleHook], None]

    def on_startup(self, hook: LifecycleHook) -> None:
        self._register_startup(hook)

    def on_shutdown(self, hook: LifecycleHook) -> None:
        self._register_shutdown(hook)

    @property
    def metrics(self) -> WeatherBotMetrics:
        return self.container.get(WeatherBotMetrics)

    @property
    def tracer(self) -> Tracer:
        return self.container.get(Tracer)

    @property
    def health(self) -> HealthMonitor:
        return self.container.get(HealthMonitor)


class Module(Protocol):
    name: str
    order: int

    def setup(self, context: ModuleContext) -> None: ...


class ModuleLoader:
    """Executes module setup in a deterministic order."""

    def __init__(self, modules: Iterable[Module]) -> None:
        self._modules = sorted(modules, key=lambda module: module.order)
        self._startup_hooks: List[LifecycleHook] = []
        self._shutdown_hooks: List[LifecycleHook] = []

    def setup(self, context: ModuleContext) -> None:
        for module in self._modules:
            module.setup(context)

    def register_startup(self, hook: LifecycleHook) -> None:
        self._startup_hooks.append(hook)

    def register_shutdown(self, hook: LifecycleHook) -> None:
        self._shutdown_hooks.append(hook)

    async def run_startup(self) -> None:
        for hook in self._startup_hooks:
            result = hook()
            if inspect.isawaitable(result):
                await result

    async def run_shutdown(self) -> None:
        for hook in reversed(self._shutdown_hooks):
            result = hook()
            if inspect.isawaitable(result):
                await result
