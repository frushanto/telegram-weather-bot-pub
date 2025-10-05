"""Event bus and mediator primitives used for module communication."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "Mediator",
    "Request",
]


TEvent = TypeVar("TEvent", bound="Event")
TRequest = TypeVar("TRequest", bound="Request")
TResponse = TypeVar("TResponse")


EventHandler = Callable[[TEvent], Awaitable[None] | None]
RequestHandler = Callable[[TRequest], Awaitable[TResponse] | TResponse]


@dataclass(frozen=True)
class Event:
    """Base type for events dispatched across the application."""

    @property
    def name(self) -> str:
        """Return the canonical name of the event."""

        return type(self).__name__


class EventBus:
    """Simple in-memory asynchronous event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], List[EventHandler[Any]]] = {}

    def subscribe(
        self, event_type: Type[TEvent], handler: EventHandler[TEvent]
    ) -> None:
        """Register a handler for the given event type."""

        handlers = self._subscribers.setdefault(event_type, [])
        handlers.append(handler)  # type: ignore[arg-type]

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching handlers."""

        for registered_type, handlers in self._subscribers.items():
            if issubclass(type(event), registered_type):
                for handler in handlers:
                    result = handler(event)  # type: ignore[arg-type]
                    if inspect.isawaitable(result):
                        await result


class Request:
    """Base class for mediator requests (commands/queries)."""


class Mediator(Generic[TRequest, TResponse]):
    """Mediator to decouple request handlers from senders."""

    def __init__(self) -> None:
        self._handlers: Dict[Type[Any], RequestHandler[Any, Any]] = {}

    def register(self, request_type: Type[TRequest], handler: RequestHandler[TRequest]):
        """Register a handler for the given request type."""

        self._handlers[request_type] = handler  # type: ignore[assignment]

    async def send(self, request: TRequest) -> Any:
        """Execute a request and return its result."""

        handler: Optional[RequestHandler[Any]] = self._handlers.get(type(request))
        if handler is None:
            raise ValueError(
                f"No handler registered for request {type(request).__name__}"
            )

        result = handler(request)
        if inspect.isawaitable(result):
            return await result
        return result

    def send_sync(self, request: TRequest) -> Any:
        """Synchronously resolve a request."""

        handler: Optional[RequestHandler[Any]] = self._handlers.get(type(request))
        if handler is None:
            raise ValueError(
                f"No handler registered for request {type(request).__name__}"
            )

        result = handler(request)
        if inspect.isawaitable(result):
            raise RuntimeError(
                "Handler for %s returned coroutine; use send() instead"
                % type(request).__name__
            )
        return result
