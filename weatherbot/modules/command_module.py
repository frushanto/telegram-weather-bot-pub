"""Module registering user facing commands and message handlers."""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from ..__version__ import __release_date__, __supported_languages__, __version__
from ..application.interfaces import (
    ConversationStateStoreProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from ..core.config import ConfigProvider
from ..handlers import commands as user_commands
from ..handlers.commands import CommandHandlerDependencies, configure_command_handlers
from ..handlers.language import (
    LanguageHandlerDependencies,
    configure_language_handlers,
    language_callback,
)
from ..handlers.messages import (
    MessageHandlerDependencies,
    configure_message_handlers,
    on_location,
    on_text,
)
from ..infrastructure.quota_notifications import QuotaNotifier
from ..jobs.scheduler import (
    SchedulerDependencies,
    configure_scheduler,
    schedule_daily_timezone_aware,
)
from ..presentation.command_presenter import CommandPresenter
from ..presentation.formatter import format_weather
from ..presentation.i18n import Localization, i18n
from ..presentation.keyboards import main_keyboard
from ..presentation.subscription_presenter import SubscriptionPresenter
from .base import Module, ModuleContext
from .events import CommandCompleted, CommandFailed, CommandInvoked

HandlerFunc = Callable[..., Awaitable[object] | object]


@dataclass
class CommandModule(Module):
    name: str = "commands"
    order: int = 20

    def setup(self, context: ModuleContext) -> None:  # noqa: D401
        application = context.application
        event_bus = context.event_bus
        tracer = context.tracer

        container = context.container
        user_service = container.get(UserServiceProtocol)
        weather_service = container.get(WeatherApplicationServiceProtocol)
        subscription_service = container.get(SubscriptionServiceProtocol)
        state_store = container.get(ConversationStateStoreProtocol)
        localization = container.get(Localization)
        quota_manager = container.get(WeatherQuotaManagerProtocol)
        config_provider = container.get(ConfigProvider)

        quota_notifier = QuotaNotifier(
            quota_manager=quota_manager,
            localization=localization,
            config_provider=config_provider.get,
        )

        command_presenter = CommandPresenter(
            user_service,
            weather_service,
            i18n.get,
            state_store,
            weather_formatter=format_weather,
            help_context={
                "version": __version__,
                "release_date": __release_date__,
                "languages": __supported_languages__,
            },
        )
        subscription_presenter = SubscriptionPresenter(
            subscription_service,
            user_service,
            i18n.get,
            state_store,
        )

        configure_language_handlers(
            LanguageHandlerDependencies(
                user_service=user_service,
                localization=localization,
                keyboard_factory=main_keyboard,
            )
        )

        configure_command_handlers(
            CommandHandlerDependencies(
                command_presenter=command_presenter,
                subscription_presenter=subscription_presenter,
                user_service=user_service,
                state_store=state_store,
                quota_notifier=quota_notifier,
                schedule_subscription=schedule_daily_timezone_aware,
            )
        )
        configure_message_handlers(
            MessageHandlerDependencies(
                user_service=user_service,
                weather_service=weather_service,
                state_store=state_store,
                subscription_presenter=subscription_presenter,
                quota_notifier=quota_notifier,
                schedule_subscription=schedule_daily_timezone_aware,
                weather_formatter=format_weather,
            )
        )
        configure_scheduler(
            SchedulerDependencies(
                user_service=user_service,
                weather_service=weather_service,
                quota_notifier=quota_notifier,
                weather_formatter=format_weather,
                translate=i18n.get,
                config_provider=config_provider.get,
            )
        )

        # Wrap every handler to emit telemetry and duration metrics around execution.
        def wrap(command: str, handler: HandlerFunc) -> HandlerFunc:
            async def _wrapper(update, tg_context):
                start = time.perf_counter()
                user = getattr(update, "effective_user", None)
                chat = getattr(update, "effective_chat", None)
                user_id = getattr(user, "id", None)
                chat_id = getattr(chat, "id", None)
                await event_bus.publish(
                    CommandInvoked(command=command, user_id=user_id, chat_id=chat_id)
                )
                try:
                    with tracer.span(
                        f"command.{command}", user_id=user_id, chat_id=chat_id
                    ):
                        result = handler(update, tg_context)
                        if inspect.isawaitable(result):
                            await result
                    duration = (time.perf_counter() - start) * 1000
                    await event_bus.publish(
                        CommandCompleted(command=command, duration_ms=duration)
                    )
                except (
                    Exception
                ) as exc:  # pragma: no cover - delegated to existing tests
                    await event_bus.publish(
                        CommandFailed(command=command, error=str(exc))
                    )
                    raise

            return _wrapper

        command_map = {
            "start": user_commands.start_cmd,
            "help": user_commands.help_cmd,
            "weather": user_commands.weather_cmd,
            "sethome": user_commands.sethome_cmd,
            "home": user_commands.home_cmd,
            "unsethome": user_commands.unsethome_cmd,
            "subscribe": user_commands.subscribe_cmd,
            "unsubscribe": user_commands.unsubscribe_cmd,
            "whoami": user_commands.whoami_cmd,
            "privacy": user_commands.privacy_cmd,
            "data": user_commands.data_cmd,
            "delete_me": user_commands.delete_me_cmd,
            "cancel": user_commands.cancel_cmd,
            "language": user_commands.language_cmd,
        }

        for name, handler in command_map.items():
            application.add_handler(CommandHandler(name, wrap(name, handler)))

        application.add_handler(MessageHandler(filters.LOCATION, on_location))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, on_text)
        )

        application.add_handler(
            CallbackQueryHandler(language_callback, pattern="^lang_")
        )
