import asyncio
import datetime
import logging
import sys
from pathlib import Path

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from weatherbot import __version__
from weatherbot.core.config import get_config
from weatherbot.core.exceptions import ConfigurationError
from weatherbot.handlers.commands import (
    cancel_cmd,
    data_cmd,
    delete_me_cmd,
    help_cmd,
    home_cmd,
    language_cmd,
    privacy_cmd,
    sethome_cmd,
    start_cmd,
    subscribe_cmd,
    unsethome_cmd,
    unsubscribe_cmd,
    weather_cmd,
    whoami_cmd,
)
from weatherbot.handlers.messages import on_location, on_text
from weatherbot.infrastructure.setup import (
    get_subscription_service,
    setup_container,
)
from weatherbot.jobs.backup import schedule_daily_backup
from weatherbot.jobs.scheduler import schedule_daily_timezone_aware

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


def get_admin_commands():

    config = get_config()
    if config.admin_ids:
        from weatherbot.handlers.admin_commands import (
            admin_backup_now_cmd,
            admin_cleanup_cmd,
            admin_config_cmd,
            admin_help_cmd,
            admin_quota_cmd,
            admin_stats_cmd,
            admin_subscriptions_cmd,
            admin_test_weather_cmd,
            admin_unblock_cmd,
            admin_user_info_cmd,
            admin_version_cmd,
        )

        return (
            admin_stats_cmd,
            admin_unblock_cmd,
            admin_user_info_cmd,
            admin_cleanup_cmd,
            admin_subscriptions_cmd,
            admin_backup_now_cmd,
            admin_config_cmd,
            admin_test_weather_cmd,
            admin_quota_cmd,
            admin_help_cmd,
            admin_version_cmd,
        )
    return None


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    try:

        config = get_config()

        setup_container()

        app = Application.builder().token(config.token).build()

        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("weather", weather_cmd))
        app.add_handler(CommandHandler("sethome", sethome_cmd))
        app.add_handler(CommandHandler("home", home_cmd))
        app.add_handler(CommandHandler("unsethome", unsethome_cmd))
        app.add_handler(CommandHandler("subscribe", subscribe_cmd))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
        app.add_handler(CommandHandler("whoami", whoami_cmd))
        app.add_handler(CommandHandler("privacy", privacy_cmd))
        app.add_handler(CommandHandler("data", data_cmd))
        app.add_handler(CommandHandler("delete_me", delete_me_cmd))
        app.add_handler(CommandHandler("cancel", cancel_cmd))
        app.add_handler(CommandHandler("language", language_cmd))

        admin_commands = get_admin_commands()
        if admin_commands:
            (
                admin_stats_cmd,
                admin_unblock_cmd,
                admin_user_info_cmd,
                admin_cleanup_cmd,
                admin_subscriptions_cmd,
                admin_backup_now_cmd,
                admin_config_cmd,
                admin_test_weather_cmd,
                admin_quota_cmd,
                admin_help_cmd,
                admin_version_cmd,
            ) = admin_commands
            app.add_handler(CommandHandler("admin_stats", admin_stats_cmd))
            app.add_handler(CommandHandler("admin_unblock", admin_unblock_cmd))
            app.add_handler(CommandHandler("admin_user_info", admin_user_info_cmd))
            app.add_handler(CommandHandler("admin_cleanup", admin_cleanup_cmd))
            app.add_handler(
                CommandHandler("admin_subscriptions", admin_subscriptions_cmd)
            )
            app.add_handler(CommandHandler("admin_backup", admin_backup_now_cmd))
            app.add_handler(CommandHandler("admin_config", admin_config_cmd))
            app.add_handler(
                CommandHandler("admin_test_weather", admin_test_weather_cmd)
            )
            app.add_handler(CommandHandler("admin_quota", admin_quota_cmd))
            app.add_handler(CommandHandler("admin_help", admin_help_cmd))
            app.add_handler(CommandHandler("admin_version", admin_version_cmd))

        app.add_handler(MessageHandler(filters.LOCATION, on_location))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

        from weatherbot.handlers.language import language_callback

        app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

        async def restore_subscriptions():
            try:
                subscription_service = get_subscription_service()
                subscriptions = await subscription_service.get_all_subscriptions_dict()
                for chat_id, sub_info in subscriptions.items():
                    await schedule_daily_timezone_aware(
                        app.job_queue,
                        int(chat_id),
                        sub_info["hour"],
                        sub_info.get("minute", 0),
                    )
                    logger.info(f"Restored subscription for user {chat_id}")
            except Exception as e:
                logger.error(f"Error restoring subscriptions: {e}")

        async def run_restore():
            await restore_subscriptions()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(run_restore())

        from weatherbot.infrastructure.spam_protection import spam_protection

        async def cleanup_spam_data(context):
            await spam_protection.cleanup_old_data()
            logger.info("Completed spam protection data cleanup")

        app.job_queue.run_daily(
            cleanup_spam_data, time=datetime.time(2, 0), name="cleanup_spam_data"
        )

        schedule_daily_backup(app.job_queue)

        logger.info(f"Telegram Weather Bot v{__version__} started")
        app.run_polling(allowed_updates=None)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception:
        logger.exception("Bot startup error")
        raise


if __name__ == "__main__":
    main()
