import logging
from typing import List, Optional, Tuple, cast

from ..core.exceptions import StorageError, ValidationError
from ..domain.repositories import UserRepository
from ..domain.value_objects import (
    SubscriptionEntry,
    UserProfile,
    UserSubscription,
)
from .dtos import SubscriptionScheduleDTO, SubscriptionScheduleMap

logger = logging.getLogger(__name__)


class SubscriptionService:

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository

    async def set_subscription(self, chat_id: str, hour: int, minute: int = 0) -> None:

        try:

            if not (0 <= hour <= 23):
                raise ValidationError(f"Invalid hour: {hour}. Must be 0-23")
            if not (0 <= minute <= 59):
                raise ValidationError(f"Invalid minute: {minute}. Must be 0-59")

            raw_data = await self._user_repo.get_user_data(str(chat_id)) or {}
            profile = UserProfile.from_storage(raw_data)

            if profile.home is None:
                raise ValidationError(
                    "Home location must be set before subscribing to weather notifications"
                )

            profile.subscription = UserSubscription(hour=hour, minute=minute)
            await self._user_repo.save_user_data(str(chat_id), profile.to_storage())

            timezone_info = ""
            if profile.home and profile.home.timezone:
                timezone_info = f" (timezone: {profile.home.timezone})"

            logger.info(
                f"Subscription set for user {chat_id} at {hour:02d}:{minute:02d}{timezone_info}"
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error setting subscription for user {chat_id}")
            raise StorageError(f"Failed to set subscription: {e}")

    async def remove_subscription(self, chat_id: str) -> bool:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            if not user_data:
                return False

            profile = UserProfile.from_storage(user_data)
            had_subscription = profile.subscription is not None
            if not had_subscription:
                return False

            profile.subscription = None

            if profile.is_empty():
                await self._user_repo.delete_user_data(str(chat_id))
            else:
                await self._user_repo.save_user_data(str(chat_id), profile.to_storage())
            logger.info(f"Subscription removed for user {chat_id}")
            return True
        except Exception as e:
            logger.exception(f"Error removing subscription for user {chat_id}")
            raise StorageError(f"Failed to remove subscription: {e}")

    async def get_subscription(self, chat_id: str) -> Optional[UserSubscription]:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            if not user_data:
                return None
            profile = UserProfile.from_storage(user_data)
            return profile.subscription
        except Exception:
            logger.exception(f"Error retrieving subscription for user {chat_id}")
            return None

    async def get_all_subscriptions(self) -> List[SubscriptionEntry]:

        try:
            all_users = await self._user_repo.get_all_users()
            subscriptions: List[SubscriptionEntry] = []
            for chat_id, user_data in all_users.items():
                profile = UserProfile.from_storage(user_data)
                if not profile.subscription:
                    continue
                subscriptions.append(
                    SubscriptionEntry(
                        chat_id=str(chat_id),
                        subscription=profile.subscription,
                        home=profile.home,
                        language=profile.language,
                    )
                )
            logger.debug(f"Found {len(subscriptions)} active subscriptions")
            return subscriptions
        except Exception as e:
            logger.exception("Error retrieving all subscriptions")
            raise StorageError(f"Failed to fetch subscriptions: {e}")

    async def unsubscribe_user(self, chat_id: str) -> bool:

        return await self.remove_subscription(chat_id)

    async def get_subscription_info(self, chat_id: str) -> Optional[UserSubscription]:

        try:
            subscription = await self.get_subscription(chat_id)
            return subscription
        except Exception:
            logger.exception(f"Error retrieving subscription info for {chat_id}")
            return None

    async def get_all_subscriptions_dict(self) -> SubscriptionScheduleMap:

        try:
            subscriptions = await self.get_all_subscriptions()
            result: SubscriptionScheduleMap = {}
            for entry in subscriptions:
                result[entry.chat_id] = SubscriptionScheduleDTO(
                    hour=entry.subscription.hour,
                    minute=entry.subscription.minute,
                )
            return result
        except Exception:
            logger.exception("Error building subscriptions dictionary")
            return cast(SubscriptionScheduleMap, {})

    async def parse_time_string(self, time_str: str) -> Tuple[int, int]:

        try:
            time_str = time_str.strip()
            if ":" in time_str:
                parts = time_str.split(":", 1)
                hour = int(parts[0])
                minute = int(parts[1]) if parts[1] else 0
            else:
                hour = int(time_str)
                minute = 0

            if not (0 <= hour <= 23):
                raise ValidationError(f"Invalid hour: {hour}. Must be 0-23")
            if not (0 <= minute <= 59):
                raise ValidationError(f"Invalid minute: {minute}. Must be 0-59")
            return hour, minute
        except (ValueError, IndexError):
            raise ValidationError(f"Invalid time format: '{time_str}'. Use HH:MM or HH")
        except ValidationError:
            raise
