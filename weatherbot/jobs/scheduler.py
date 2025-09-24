import logging
from datetime import time as dtime

import pytz
from telegram.ext import ContextTypes

from weatherbot.core.config import get_config
from weatherbot.core.exceptions import (
    StorageError,
    ValidationError,
    WeatherServiceError,
)
from weatherbot.infrastructure.setup import (
    get_user_service,
    get_weather_application_service,
)
from weatherbot.presentation.formatter import format_weather
from weatherbot.presentation.i18n import i18n

logger = logging.getLogger(__name__)


def _job_name(chat_id: int) -> str:
    return f"daily-{chat_id}"


async def schedule_daily_timezone_aware(
    job_queue, chat_id: int, hour: int, minute: int = 0
):
    """Schedule daily job using user's timezone or fallback to system timezone"""

    for job in job_queue.get_jobs_by_name(_job_name(chat_id)):
        job.schedule_removal()

    try:
        # Get user's timezone
        user_service = get_user_service()
        user_data = await user_service.get_user_data(str(chat_id))

        if user_data and "timezone" in user_data:
            # Use user's timezone
            user_timezone = pytz.timezone(user_data["timezone"])
            logger.info(
                f"Scheduling subscription for user {chat_id} using timezone {user_data['timezone']}"
            )
        else:
            # Fallback to system timezone
            config = get_config()
            user_timezone = config.timezone
            logger.info(
                f"Scheduling subscription for user {chat_id} using fallback timezone {config.timezone}"
            )
    except Exception as e:
        # Fallback to system timezone if any error occurs
        config = get_config()
        user_timezone = config.timezone
        logger.warning(
            f"Error getting user timezone for {chat_id}, using fallback: {e}"
        )

    job_queue.run_daily(
        send_home_weather,
        time=dtime(hour=hour, minute=minute, tzinfo=user_timezone),
        name=_job_name(chat_id),
        chat_id=chat_id,
    )


def schedule_daily(job_queue, chat_id: int, hour: int, minute: int = 0):
    """Legacy synchronous wrapper - will be deprecated"""
    import asyncio

    # For backward compatibility, run the async version
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an existing event loop, schedule as a task
            asyncio.create_task(
                schedule_daily_timezone_aware(job_queue, chat_id, hour, minute)
            )
        else:
            # If no event loop is running, run it
            loop.run_until_complete(
                schedule_daily_timezone_aware(job_queue, chat_id, hour, minute)
            )
    except Exception as e:
        logger.exception(f"Error in legacy schedule_daily wrapper: {e}")
        # Fallback to old behavior
        for job in job_queue.get_jobs_by_name(_job_name(chat_id)):
            job.schedule_removal()

        config = get_config()
        job_queue.run_daily(
            send_home_weather,
            time=dtime(hour=hour, minute=minute, tzinfo=config.timezone),
            name=_job_name(chat_id),
            chat_id=chat_id,
        )


async def send_home_weather(context: ContextTypes.DEFAULT_TYPE) -> None:

    chat_id = context.job.chat_id
    try:
        user_service = get_user_service()
        weather_service = get_weather_application_service()

        user_data = await user_service.get_user_data(str(chat_id))
        if not user_data or "lat" not in user_data or "lon" not in user_data:
            user_lang = await user_service.get_user_language(str(chat_id)) or "ru"
            await context.bot.send_message(chat_id, i18n.get("home_not_set", user_lang))
            return

        user_lang = await user_service.get_user_language(str(chat_id)) or "ru"

        weather_data = await weather_service.get_weather_by_coordinates(
            user_data["lat"], user_data["lon"]
        )

        msg = format_weather(
            weather_data, place_label=user_data.get("label"), lang=user_lang
        )
        await context.bot.send_message(chat_id, msg, parse_mode="HTML")
        logger.debug(f"Sent home weather to user {chat_id}")
    except (ValidationError, StorageError, WeatherServiceError) as e:
        logger.error(f"Error sending home weather to user {chat_id}: {e}")
        user_lang = await user_service.get_user_language(str(chat_id)) or "ru"
        await context.bot.send_message(chat_id, i18n.get("weather_error", user_lang))
    except Exception:
        logger.exception(f"Unexpected error sending weather to user {chat_id}")
        user_lang = await user_service.get_user_language(str(chat_id)) or "ru"
        await context.bot.send_message(chat_id, i18n.get("weather_error", user_lang))
