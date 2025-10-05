import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Set, Tuple

from weatherbot.core.config import SpamConfig, get_config
from weatherbot.core.container import get_container
from weatherbot.domain.services import SpamProtectionService
from weatherbot.presentation.i18n import Localization

logger = logging.getLogger(__name__)


def get_spam_config() -> SpamConfig:
    return get_config().spam_config


class UserActivity:
    def __init__(self) -> None:
        self.request_times: list[float] = []
        self.last_request_time: float = 0
        self.blocked_until: float = 0
        self.block_count: int = 0
        self.daily_requests: int = 0
        self.last_reset_date: str = ""
        self.last_block_notification: float = 0


class SpamProtection(SpamProtectionService):
    def __init__(
        self,
        *,
        config_provider: Optional[Callable[[], SpamConfig]] = None,
        translator: Optional[Callable[..., str]] = None,
    ) -> None:
        self._config_provider = config_provider or (lambda: get_config().spam_config)
        self._translator = translator or (
            lambda key, lang, **kwargs: get_container()
            .get(Localization)
            .get(key, lang, **kwargs)
        )
        self._user_activities: Dict[int, UserActivity] = {}
        self._blocked_users: Set[int] = set()
        self._spam_lock = asyncio.Lock()

    async def is_spam(
        self,
        user_id: int,
        message_text: str = "",
        *,
        count_request: bool = True,
        user_lang: str = "ru",
    ) -> Tuple[bool, str]:
        async with self._spam_lock:
            current_time = time.time()
            today = datetime.now().strftime("%Y-%m-%d")

            if user_id not in self._user_activities:
                self._user_activities[user_id] = UserActivity()
            activity = self._user_activities[user_id]

            if activity.last_reset_date != today:
                activity.daily_requests = 0
                activity.last_reset_date = today

            if activity.blocked_until > current_time:
                remaining = int(activity.blocked_until - current_time)
                time_since_last_notification = (
                    current_time - activity.last_block_notification
                )
                if (
                    activity.last_block_notification == 0
                    or time_since_last_notification > 300
                ):
                    activity.last_block_notification = current_time
                    return True, self._translate(
                        "spam_blocked_message", user_lang, seconds=remaining
                    )
                return True, "SILENT_BLOCK"

            config = self._config()

            if len(message_text) > config.max_message_length:
                await self._block_user(user_id, "Message too long")
                return True, self._translate("spam_message_too_long", user_lang)

            time_since_last = current_time - activity.last_request_time
            if time_since_last < config.min_cooldown:
                cooldown_remaining = config.min_cooldown - time_since_last
                logger.debug(
                    "Spam check: user=%s too fast: %.3fs < min_cooldown=%s",
                    user_id,
                    time_since_last,
                    config.min_cooldown,
                )
                return True, self._translate(
                    "spam_warning_title", user_lang, seconds=f"{cooldown_remaining:.1f}"
                )

            if count_request:
                activity.request_times = [
                    req_time
                    for req_time in activity.request_times
                    if current_time - req_time < 3600
                ]

                minute_ago = current_time - 60
                requests_last_minute = sum(
                    1 for req_time in activity.request_times if req_time > minute_ago
                )
                if requests_last_minute >= config.max_requests_per_minute:
                    logger.debug(
                        "Spam check: user=%s requests_last_minute=%s >= max_per_minute=%s",
                        user_id,
                        requests_last_minute,
                        config.max_requests_per_minute,
                    )
                    await self._block_user(user_id, "Rate limit per minute exceeded")
                    return True, self._translate("spam_rate_limit_minute", user_lang)

                hour_ago = current_time - 3600
                requests_last_hour = sum(
                    1 for req_time in activity.request_times if req_time > hour_ago
                )
                if requests_last_hour >= config.max_requests_per_hour:
                    logger.debug(
                        "Spam check: user=%s requests_last_hour=%s >= max_per_hour=%s",
                        user_id,
                        requests_last_hour,
                        config.max_requests_per_hour,
                    )
                    await self._block_user(user_id, "Rate limit per hour exceeded")
                    return True, self._translate("spam_rate_limit_hour", user_lang)

                if activity.daily_requests >= config.max_requests_per_day:
                    logger.debug(
                        "Spam check: user=%s daily_requests=%s >= max_per_day=%s",
                        user_id,
                        activity.daily_requests,
                        config.max_requests_per_day,
                    )
                    await self._block_user(user_id, "Daily limit exceeded")
                    return True, self._translate("spam_daily_limit", user_lang)

                activity.request_times.append(current_time)
                activity.last_request_time = current_time
                activity.daily_requests += 1
            else:
                activity.last_request_time = current_time

            return False, ""

    async def _block_user(self, user_id: int, reason: str) -> None:
        if user_id not in self._user_activities:
            self._user_activities[user_id] = UserActivity()
        activity = self._user_activities[user_id]
        activity.block_count += 1

        config = self._config()
        if activity.block_count > 1:
            block_duration = config.extended_block_duration
        else:
            block_duration = config.block_duration
        activity.blocked_until = time.time() + block_duration

        activity.last_block_notification = 0
        self._blocked_users.add(user_id)
        logger.warning(
            "User %s blocked for %s sec. Reason: %s. Offense #%s",
            user_id,
            block_duration,
            reason,
            activity.block_count,
        )

    async def unblock_user(self, user_id: int) -> bool:
        if user_id in self._user_activities:
            self._user_activities[user_id].blocked_until = 0
            self._user_activities[user_id].last_block_notification = 0
            self._blocked_users.discard(user_id)
            logger.info("User %s unblocked", user_id)
            return True
        return False

    async def get_user_stats(self, user_id: int) -> Dict:
        if user_id not in self._user_activities:
            return {"requests_today": 0, "is_blocked": False, "block_count": 0}
        activity = self._user_activities[user_id]
        current_time = time.time()
        return {
            "requests_today": activity.daily_requests,
            "is_blocked": activity.blocked_until > current_time,
            "block_count": activity.block_count,
            "blocked_until": (
                activity.blocked_until
                if activity.blocked_until > current_time
                else None
            ),
        }

    def get_user_activity_snapshot(self) -> Mapping[int, Any]:
        return dict(self._user_activities)

    def get_blocked_users(self) -> Iterable[int]:
        return set(self._blocked_users)

    async def cleanup_old_data(self) -> None:
        current_time = time.time()
        users_to_remove = []
        for user_id, activity in self._user_activities.items():
            if (current_time - activity.last_request_time) > (30 * 24 * 3600):
                users_to_remove.append(user_id)
        for user_id in users_to_remove:
            del self._user_activities[user_id]
            self._blocked_users.discard(user_id)
        if users_to_remove:
            logger.info("Purged data for %s inactive users", len(users_to_remove))

    @property
    def user_activities(self) -> Dict[int, UserActivity]:
        return self._user_activities

    @property
    def blocked_users(self) -> Set[int]:
        return self._blocked_users

    def _config(self) -> SpamConfig:
        return self._config_provider()

    def _translate(self, key: str, lang: str, **kwargs: Any) -> str:
        try:
            return self._translator(key, lang, **kwargs)
        except Exception:
            return key
