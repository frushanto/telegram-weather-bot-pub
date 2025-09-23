import logging
from typing import Dict, List, Optional, Tuple

from ..core.exceptions import StorageError, ValidationError
from ..domain.repositories import UserRepository

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
            user_data = await self._user_repo.get_user_data(str(chat_id)) or {}
            user_data.update({"sub_hour": hour, "sub_min": minute})
            await self._user_repo.save_user_data(str(chat_id), user_data)
            logger.info(
                f"Subscription set for user {chat_id} at {hour:02d}:{minute:02d}"
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

            had_subscription = "sub_hour" in user_data

            user_data.pop("sub_hour", None)
            user_data.pop("sub_min", None)

            if user_data:
                await self._user_repo.save_user_data(str(chat_id), user_data)
            else:
                await self._user_repo.delete_user_data(str(chat_id))
            if had_subscription:
                logger.info(f"Subscription removed for user {chat_id}")
            return had_subscription
        except Exception as e:
            logger.exception(f"Error removing subscription for user {chat_id}")
            raise StorageError(f"Failed to remove subscription: {e}")

    async def get_subscription(self, chat_id: str) -> Optional[Tuple[int, int]]:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            if not user_data:
                return None
            hour = user_data.get("sub_hour")
            minute = user_data.get("sub_min", 0)
            if isinstance(hour, int) and 0 <= hour <= 23:
                return hour, int(minute) if isinstance(minute, int) else 0
            return None
        except Exception:
            logger.exception(f"Error retrieving subscription for user {chat_id}")
            return None

    async def get_all_subscriptions(self) -> List[Dict]:

        try:
            all_users = await self._user_repo.get_all_users()
            subscriptions = []
            for chat_id, user_data in all_users.items():
                hour = user_data.get("sub_hour")
                minute = user_data.get("sub_min", 0)
                if isinstance(hour, int) and 0 <= hour <= 23:
                    subscriptions.append(
                        {
                            "chat_id": chat_id,
                            "hour": hour,
                            "minute": int(minute) if isinstance(minute, int) else 0,
                            "user_data": user_data,
                        }
                    )
            logger.debug(f"Found {len(subscriptions)} active subscriptions")
            return subscriptions
        except Exception as e:
            logger.exception("Error retrieving all subscriptions")
            raise StorageError(f"Failed to fetch subscriptions: {e}")

    async def unsubscribe_user(self, chat_id: str) -> bool:

        return await self.remove_subscription(chat_id)

    async def get_subscription_info(self, chat_id: str) -> Optional[Dict]:

        try:
            subscription = await self.get_subscription(chat_id)
            if subscription:
                hour, minute = subscription
                return {"hour": hour, "minute": minute}
            return None
        except Exception:
            logger.exception(f"Error retrieving subscription info for {chat_id}")
            return None

    async def get_all_subscriptions_dict(self) -> Dict[str, Dict]:

        try:
            subscriptions = await self.get_all_subscriptions()
            result = {}
            for sub in subscriptions:
                result[sub["chat_id"]] = {"hour": sub["hour"], "minute": sub["minute"]}
            return result
        except Exception:
            logger.exception("Error building subscriptions dictionary")
            return {}

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
