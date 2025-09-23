import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Set, Tuple

from weatherbot.core.config import get_config
from weatherbot.presentation.i18n import i18n

logger = logging.getLogger(__name__)

spam_config = None


def get_spam_config():
    global spam_config
    if spam_config is None:
        config = get_config()
        spam_config = config.spam_config
    return spam_config


class UserActivity:
    def __init__(self):

        self.request_times: list[float] = []

        self.last_request_time: float = 0

        self.blocked_until: float = 0

        self.block_count: int = 0

        self.daily_requests: int = 0

        self.last_reset_date: str = ""

        self.last_block_notification: float = 0


class SpamProtection:
    def __init__(self):
        self.user_activities: Dict[int, UserActivity] = {}
        self.blocked_users: Set[int] = set()
        self.spam_lock = asyncio.Lock()

    async def is_spam(
        self,
        user_id: int,
        message_text: str = "",
        count_request: bool = True,
        user_lang: str = "ru",
    ) -> Tuple[bool, str]:

        async with self.spam_lock:
            current_time = time.time()
            today = datetime.now().strftime("%Y-%m-%d")

            if user_id not in self.user_activities:
                self.user_activities[user_id] = UserActivity()
            activity = self.user_activities[user_id]

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
                    return True, i18n.get(
                        "spam_blocked_message", user_lang, seconds=remaining
                    )
                else:

                    return True, "SILENT_BLOCK"

            if len(message_text) > get_spam_config().max_message_length:
                await self._block_user(user_id, "Message too long")
                return True, i18n.get("spam_message_too_long", user_lang)

            time_since_last = current_time - activity.last_request_time
            if time_since_last < get_spam_config().min_cooldown:
                cooldown_remaining = get_spam_config().min_cooldown - time_since_last
                logger.debug(
                    f"Spam check: user={user_id} too fast: {time_since_last:.3f}s < min_cooldown={get_spam_config().min_cooldown}"
                )
                return True, i18n.get(
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

                if requests_last_minute >= get_spam_config().max_requests_per_minute:
                    logger.debug(
                        f"Spam check: user={user_id} requests_last_minute={requests_last_minute} >= max_per_minute={get_spam_config().max_requests_per_minute}"
                    )
                    await self._block_user(user_id, "Rate limit per minute exceeded")
                    return True, i18n.get("spam_rate_limit_minute", user_lang)

                hour_ago = current_time - 3600
                requests_last_hour = sum(
                    1 for req_time in activity.request_times if req_time > hour_ago
                )

                if requests_last_hour >= get_spam_config().max_requests_per_hour:
                    logger.debug(
                        f"Spam check: user={user_id} requests_last_hour={requests_last_hour} >= max_per_hour={get_spam_config().max_requests_per_hour}"
                    )
                    await self._block_user(user_id, "Rate limit per hour exceeded")
                    return True, i18n.get("spam_rate_limit_hour", user_lang)

                if activity.daily_requests >= get_spam_config().max_requests_per_day:
                    logger.debug(
                        f"Spam check: user={user_id} daily_requests={activity.daily_requests} >= max_per_day={get_spam_config().max_requests_per_day}"
                    )
                    await self._block_user(user_id, "Daily limit exceeded")
                    return True, i18n.get("spam_daily_limit", user_lang)

                activity.request_times.append(current_time)
                activity.last_request_time = current_time
                activity.daily_requests += 1
            else:

                activity.last_request_time = current_time
            return False, ""

    async def _block_user(self, user_id: int, reason: str) -> None:

        if user_id not in self.user_activities:
            self.user_activities[user_id] = UserActivity()
        activity = self.user_activities[user_id]
        activity.block_count += 1

        if activity.block_count > 1:
            block_duration = get_spam_config().extended_block_duration
        else:
            block_duration = get_spam_config().block_duration
        activity.blocked_until = time.time() + block_duration

        activity.last_block_notification = 0
        self.blocked_users.add(user_id)
        logger.warning(
            f"User {user_id} blocked for {block_duration} sec. "
            f"Reason: {reason}. Offense #{activity.block_count}"
        )

    async def unblock_user(self, user_id: int) -> bool:

        if user_id in self.user_activities:
            self.user_activities[user_id].blocked_until = 0

            self.user_activities[user_id].last_block_notification = 0
            self.blocked_users.discard(user_id)
            logger.info(f"User {user_id} unblocked")
            return True
        return False

    def get_user_stats(self, user_id: int) -> dict:

        if user_id not in self.user_activities:
            return {"requests_today": 0, "is_blocked": False, "block_count": 0}
        activity = self.user_activities[user_id]
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

    async def cleanup_old_data(self) -> None:

        current_time = time.time()
        users_to_remove = []
        for user_id, activity in self.user_activities.items():

            if (current_time - activity.last_request_time) > (30 * 24 * 3600):
                users_to_remove.append(user_id)
        for user_id in users_to_remove:
            del self.user_activities[user_id]
            self.blocked_users.discard(user_id)
        if users_to_remove:
            logger.info(f"Purged data for {len(users_to_remove)} inactive users")


spam_protection = SpamProtection()
