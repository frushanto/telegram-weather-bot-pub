import pytest

from weatherbot.core.events import Event, EventBus, Mediator, Request


class _SampleEvent(Event):
    def __init__(self, payload: str) -> None:
        self.payload = payload


class _SampleRequest(Request):
    def __init__(self, value: int) -> None:
        self.value = value


@pytest.mark.asyncio
async def test_event_bus_supports_async_and_sync_handlers() -> None:
    bus = EventBus()
    events: list[str] = []

    async def async_handler(event: _SampleEvent) -> None:
        events.append(f"async:{event.payload}")

    def sync_handler(event: _SampleEvent) -> None:
        events.append(f"sync:{event.payload}")

    bus.subscribe(_SampleEvent, async_handler)
    bus.subscribe(_SampleEvent, sync_handler)

    await bus.publish(_SampleEvent("ping"))

    assert events == ["async:ping", "sync:ping"]


@pytest.mark.asyncio
async def test_mediator_dispatches_requests() -> None:
    mediator: Mediator[_SampleRequest, int] = Mediator()

    def handler(request: _SampleRequest) -> int:
        return request.value * 2

    mediator.register(_SampleRequest, handler)

    result = mediator.send_sync(_SampleRequest(21))
    assert result == 42

    async def async_handler(request: _SampleRequest) -> int:
        return request.value + 1

    mediator.register(_SampleRequest, async_handler)
    assert await mediator.send(_SampleRequest(41)) == 42
