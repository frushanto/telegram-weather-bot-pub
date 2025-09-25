import asyncio
import logging
from typing import Iterable

from telegram import Bot

from ..core.config import get_config
from ..presentation.i18n import i18n
from ..utils.time import format_reset_time
from .setup import get_weather_quota_manager

logger = logging.getLogger(__name__)


async def notify_quota_if_needed(bot: Bot) -> None:

    quota_manager = get_weather_quota_manager()
    status = await quota_manager.get_status()
    thresholds = status.pending_alert_thresholds
    if not thresholds:
        return

    config = get_config()
    admin_ids: Iterable[int] = config.admin_ids or []
    if not admin_ids:
        await quota_manager.mark_alert_sent(max(thresholds), status.reset_at)
        return

    admin_lang = config.admin_language
    tz_name = getattr(config.timezone, "key", None)
    reset_text = (
        format_reset_time(status.reset_at, tz_name)
        if status.reset_at
        else i18n.get("admin_quota_no_reset", admin_lang)
    )

    async def _send(admin_id: int, message: str) -> None:

        try:
            await bot.send_message(admin_id, message)
        except Exception:
            logger.exception("Failed to send quota alert to admin %s", admin_id)

    for threshold in thresholds:
        percent = int(threshold * 100)
        if threshold >= 1.0:
            message = i18n.get(
                "admin_quota_alert_exhausted",
                admin_lang,
                limit=status.limit,
                reset_time=reset_text,
            )
        else:
            message = i18n.get(
                "admin_quota_alert_threshold",
                admin_lang,
                percent=percent,
                used=status.used,
                limit=status.limit,
                remaining=status.remaining,
                reset_time=reset_text,
            )
        await asyncio.gather(*(_send(admin_id, message) for admin_id in admin_ids))

    await quota_manager.mark_alert_sent(max(thresholds), status.reset_at)
