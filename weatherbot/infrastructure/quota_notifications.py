from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Iterable

from telegram import Bot

from weatherbot.application.interfaces import WeatherQuotaManagerProtocol
from weatherbot.core.config import BotConfig
from weatherbot.presentation.i18n import Localization
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QuotaNotifier:
    """Sends administrative alerts when weather API quota nears exhaustion."""

    quota_manager: WeatherQuotaManagerProtocol
    localization: Localization
    config_provider: Callable[[], BotConfig]

    async def __call__(self, bot: Bot) -> None:
        """Notify administrators about quota thresholds when required."""

        status = await self.quota_manager.get_status()
        thresholds = status.pending_alert_thresholds
        if not thresholds:
            return

        config = self.config_provider()
        admin_ids: Iterable[int] = config.admin_ids or []
        if not admin_ids:
            await self.quota_manager.mark_alert_sent(max(thresholds), status.reset_at)
            return

        admin_lang = config.admin_language
        tz_name = getattr(config.timezone, "key", None)
        reset_text = (
            format_reset_time(status.reset_at, tz_name)
            if status.reset_at
            else self.localization.get("admin_quota_no_reset", admin_lang)
        )

        async def _send(admin_id: int, message: str) -> None:
            try:
                await bot.send_message(admin_id, message)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to send quota alert to admin %s", admin_id)

        for threshold in thresholds:
            percent = int(threshold * 100)
            if threshold >= 1.0:
                message = self.localization.get(
                    "admin_quota_alert_exhausted",
                    admin_lang,
                    limit=status.limit,
                    reset_time=reset_text,
                )
            else:
                message = self.localization.get(
                    "admin_quota_alert_threshold",
                    admin_lang,
                    percent=percent,
                    used=status.used,
                    limit=status.limit,
                    remaining=status.remaining,
                    reset_time=reset_text,
                )
            await asyncio.gather(*(_send(admin_id, message) for admin_id in admin_ids))

        await self.quota_manager.mark_alert_sent(max(thresholds), status.reset_at)


__all__ = ["QuotaNotifier"]
