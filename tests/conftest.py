import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytz

from weatherbot.application.interfaces import ConversationStateStoreProtocol
from weatherbot.core.container import (
    Container,
    get_container,
    reset_container,
    set_container,
)
from weatherbot.handlers.commands import (
    CommandHandlerDependencies,
    configure_command_handlers,
)
from weatherbot.handlers.language import (
    LanguageHandlerDependencies,
    configure_language_handlers,
)
from weatherbot.handlers.messages import (
    MessageHandlerDependencies,
    configure_message_handlers,
)
from weatherbot.infrastructure.state import ConversationStateStore
from weatherbot.jobs.scheduler import SchedulerDependencies, configure_scheduler
from weatherbot.presentation.i18n import Localization


def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        funcargs = {
            name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(pyfuncitem.obj(**funcargs))
        return True
    return None


@pytest.fixture(autouse=True)
def _container_scope():

    container = Container()
    container.register_singleton(Localization, Localization())
    set_container(container)
    yield
    reset_container()


def _ensure_state_store() -> ConversationStateStore:
    container = get_container()
    try:
        store = container.get(ConversationStateStore)
    except ValueError:
        store = ConversationStateStore()
        container.register_singleton(ConversationStateStore, store)
    container.register_singleton(ConversationStateStoreProtocol, store)
    return store


@pytest.fixture(autouse=True)
def clear_state():

    store = _ensure_state_store()
    store.reset()
    yield
    store.reset()


@pytest.fixture(autouse=True)
def configure_default_handler_dependencies():

    store = _ensure_state_store()
    container = get_container()
    command_presenter = SimpleNamespace(
        start=AsyncMock(),
        help=AsyncMock(),
        set_home=AsyncMock(),
        home_weather=AsyncMock(),
        unset_home=AsyncMock(),
        data_snapshot=AsyncMock(),
        delete_user_data=AsyncMock(),
        privacy=AsyncMock(),
        whoami=AsyncMock(),
    )
    subscription_presenter = SimpleNamespace(
        prompt_for_time=AsyncMock(),
        subscribe=AsyncMock(),
        unsubscribe=AsyncMock(),
    )
    user_service = AsyncMock()
    user_service.get_user_language = AsyncMock(return_value="ru")
    user_service.set_user_language = AsyncMock()
    user_service.get_user_home = AsyncMock(return_value=None)
    user_service.get_user_profile = AsyncMock()
    weather_service = AsyncMock()
    weather_service.get_weather_by_coordinates = AsyncMock()
    weather_service.get_weather_by_city = AsyncMock()
    weather_service.geocode_city = AsyncMock()
    quota_notifier = AsyncMock()
    schedule_mock = AsyncMock()

    # Mock bot and localization for new dependencies
    mock_bot = AsyncMock()
    from weatherbot.presentation.i18n import Localization

    localization = Localization()

    async def quota(bot):
        await quota_notifier(bot)

    async def schedule(job_queue, chat_id, hour, minute):
        await schedule_mock(job_queue, chat_id, hour, minute)

    configure_command_handlers(
        CommandHandlerDependencies(
            command_presenter=command_presenter,
            subscription_presenter=subscription_presenter,
            user_service=user_service,
            state_store=store,
            quota_notifier=quota,
            schedule_subscription=schedule,
            bot=mock_bot,
            localization=localization,
        )
    )
    configure_message_handlers(
        MessageHandlerDependencies(
            user_service=user_service,
            weather_service=weather_service,
            state_store=store,
            subscription_presenter=subscription_presenter,
            quota_notifier=quota,
            schedule_subscription=schedule,
            weather_formatter=lambda *args, **kwargs: "",
        )
    )
    configure_language_handlers(
        LanguageHandlerDependencies(
            user_service=user_service,
            localization=container.get(Localization),
            keyboard_factory=lambda _lang: None,
        )
    )
    configure_scheduler(
        SchedulerDependencies(
            user_service=user_service,
            weather_service=weather_service,
            quota_notifier=quota,
            weather_formatter=lambda *args, **kwargs: "",
            translate=lambda key, lang, **kwargs: key,
            config_provider=lambda: SimpleNamespace(timezone=pytz.UTC),
        )
    )

    yield
