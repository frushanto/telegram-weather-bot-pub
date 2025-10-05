"""Application entrypoint configuring bot modules and lifecycle."""

from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from weatherbot import __version__
from weatherbot.core.config import get_config
from weatherbot.core.events import EventBus, Mediator
from weatherbot.core.exceptions import ConfigurationError
from weatherbot.infrastructure.setup import setup_container
from weatherbot.modules.admin_module import AdminModule
from weatherbot.modules.base import ModuleContext, ModuleLoader
from weatherbot.modules.command_module import CommandModule
from weatherbot.modules.events import BotStarted
from weatherbot.modules.jobs_module import JobsModule
from weatherbot.modules.observability import ObservabilityModule

logger = logging.getLogger(__name__)


def main() -> None:
    """Configure dependency container, load modules and start polling."""

    try:
        config = get_config()
        container = setup_container()

        event_bus = container.get(EventBus)
        mediator = container.get(Mediator)

        app = Application.builder().token(config.token).build()

        loader = ModuleLoader(
            [
                ObservabilityModule(),
                AdminModule(),
                CommandModule(),
                JobsModule(),
            ]
        )

        context = ModuleContext(
            application=app,
            container=container,
            config=config,
            event_bus=event_bus,
            mediator=mediator,
            _register_startup=loader.register_startup,
            _register_shutdown=loader.register_shutdown,
        )

        loader.setup(context)

        async def _run_bot() -> None:
            await loader.run_startup()
            await event_bus.publish(BotStarted(version=__version__))
            logger.info("Telegram Weather Bot v%s started", __version__)

            async with app:
                await app.start()
                if app.updater:
                    await app.updater.start_polling(allowed_updates=None)

                    # Keep the bot running until interrupted
                    try:
                        await asyncio.Event().wait()
                    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                        logger.info("Shutdown signal received")
                    finally:
                        await app.updater.stop()
                        await app.stop()

            await loader.run_shutdown()

        try:
            asyncio.run(_run_bot())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        raise
    except Exception:
        logger.exception("Bot startup error")
        raise


if __name__ == "__main__":
    main()
