from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from weatherbot.application.interfaces import (
    ConversationStateStoreProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from weatherbot.core.config import ConfigProvider
from weatherbot.core.container import Container
from weatherbot.infrastructure.quota_notifications import QuotaNotifier
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager
from weatherbot.modules.base import ModuleContext
from weatherbot.modules.command_module import CommandModule
from weatherbot.observability.health import HealthMonitor
from weatherbot.observability.metrics import WeatherBotMetrics
from weatherbot.observability.tracing import Tracer
from weatherbot.presentation.i18n import Localization


def _make_context(container: Container) -> ModuleContext:
    application = MagicMock()
    event_bus = MagicMock()
    mediator = MagicMock()
    config = SimpleNamespace(admin_ids=[1], admin_language="en", timezone=None)

    startup_hooks: list = []
    shutdown_hooks: list = []

    return ModuleContext(
        application=application,
        container=container,
        config=config,
        event_bus=event_bus,
        mediator=mediator,
        _register_startup=startup_hooks.append,
        _register_shutdown=shutdown_hooks.append,
    )


def test_command_module_wires_handler_dependencies():
    container = Container()

    user_service = MagicMock()
    weather_service = MagicMock()
    subscription_service = MagicMock()
    state_store = MagicMock()
    localization = MagicMock(spec=Localization)
    quota_manager = MagicMock(spec=WeatherApiQuotaManager)
    config_provider = SimpleNamespace(
        get=lambda: SimpleNamespace(admin_ids=[1], admin_language="en", timezone=None)
    )

    container.register_instance(UserServiceProtocol, user_service)
    container.register_instance(WeatherApplicationServiceProtocol, weather_service)
    container.register_instance(SubscriptionServiceProtocol, subscription_service)
    container.register_instance(ConversationStateStoreProtocol, state_store)
    container.register_instance(Localization, localization)
    container.register_instance(WeatherQuotaManagerProtocol, quota_manager)
    container.register_instance(WeatherApiQuotaManager, quota_manager)
    container.register_instance(ConfigProvider, config_provider)
    container.register_instance(Tracer, MagicMock(spec=Tracer))
    container.register_instance(WeatherBotMetrics, MagicMock(spec=WeatherBotMetrics))
    container.register_instance(HealthMonitor, MagicMock(spec=HealthMonitor))

    context = _make_context(container)

    module = CommandModule()

    with (
        patch(
            "weatherbot.modules.command_module.configure_command_handlers"
        ) as mock_cmd,
        patch(
            "weatherbot.modules.command_module.configure_message_handlers"
        ) as mock_msg,
        patch("weatherbot.modules.command_module.configure_scheduler") as mock_sched,
        patch(
            "weatherbot.modules.command_module.configure_language_handlers"
        ) as mock_lang,
    ):
        module.setup(context)

    mock_cmd.assert_called_once()
    mock_msg.assert_called_once()
    mock_sched.assert_called_once()
    mock_lang.assert_called_once()

    cmd_deps = mock_cmd.call_args.args[0]
    msg_deps = mock_msg.call_args.args[0]
    sched_deps = mock_sched.call_args.args[0]
    lang_deps = mock_lang.call_args.args[0]

    assert cmd_deps.user_service is user_service
    assert msg_deps.weather_service is weather_service
    assert cmd_deps.state_store is state_store

    assert isinstance(cmd_deps.quota_notifier, QuotaNotifier)
    assert (
        cmd_deps.quota_notifier is msg_deps.quota_notifier is sched_deps.quota_notifier
    )
    assert sched_deps.config_provider is config_provider.get
    assert lang_deps.user_service is user_service
