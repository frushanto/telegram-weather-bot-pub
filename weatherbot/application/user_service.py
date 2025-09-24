import logging
from typing import Dict, Optional

from ..core.exceptions import StorageError, ValidationError
from ..domain.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self, user_repository: UserRepository, timezone_service=None):
        self._user_repo = user_repository
        self._timezone_service = timezone_service

    async def get_user_home(self, chat_id: str) -> Optional[Dict]:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            if not user_data:
                return None

            if all(key in user_data for key in ["lat", "lon", "label"]):
                home_data = {
                    "lat": user_data["lat"],
                    "lon": user_data["lon"],
                    "label": user_data["label"],
                }
                # Include timezone if available
                if "timezone" in user_data:
                    home_data["timezone"] = user_data["timezone"]
                return home_data
            return None
        except Exception as e:
            logger.exception(f"Error getting home location for user {chat_id}")
            raise StorageError(f"Failed to get home location: {e}")

    async def set_user_home(
        self, chat_id: str, lat: float, lon: float, label: str
    ) -> None:

        try:
            if not (-90 <= lat <= 90):
                raise ValidationError(f"Invalid latitude: {lat}")
            if not (-180 <= lon <= 180):
                raise ValidationError(f"Invalid longitude: {lon}")
            if not label or not label.strip():
                raise ValidationError("Location label cannot be empty")

            user_data = await self._user_repo.get_user_data(str(chat_id)) or {}
            user_data.update({"lat": lat, "lon": lon, "label": label.strip()})

            # Automatically determine timezone if timezone_service is available
            if self._timezone_service:
                timezone_name = self._timezone_service.get_timezone_by_coordinates(
                    lat, lon
                )
                if timezone_name:
                    user_data["timezone"] = timezone_name
                    logger.info(
                        f"Automatically set timezone '{timezone_name}' for user {chat_id}"
                    )
                else:
                    logger.warning(
                        f"Could not determine timezone for coordinates {lat:.4f}, {lon:.4f} for user {chat_id}"
                    )

            await self._user_repo.save_user_data(str(chat_id), user_data)
            logger.info(f"Home location set for user {chat_id}: {label}")
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error setting home location for user {chat_id}")
            raise StorageError(f"Failed to set home location: {e}")
            logger.exception(f"Error setting home location for user {chat_id}")
            raise StorageError(f"Failed to set home location: {e}")

    async def remove_user_home(self, chat_id: str) -> bool:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            if not user_data:
                return False

            home_keys = ["lat", "lon", "label", "timezone"]  # Include timezone
            had_home = any(key in user_data for key in home_keys)
            for key in home_keys:
                user_data.pop(key, None)

            if user_data:
                await self._user_repo.save_user_data(str(chat_id), user_data)
            else:

                await self._user_repo.delete_user_data(str(chat_id))
            if had_home:
                logger.info(f"Home location removed for user {chat_id}")
            return had_home
        except Exception as e:
            logger.exception(f"Error removing home location for user {chat_id}")
            raise StorageError(f"Failed to remove home location: {e}")

    async def get_user_language(self, chat_id: str) -> str:
        try:
            return await self._user_repo.get_user_language(str(chat_id))
        except Exception:
            logger.exception(f"Error getting user language {chat_id}")
            return "ru"

    async def set_user_language(self, chat_id: str, language: str) -> None:

        try:

            allowed_languages = ["ru", "en", "de"]
            if language not in allowed_languages:
                raise ValidationError(
                    f"Unsupported language: {language}. Allowed: {allowed_languages}"
                )
            await self._user_repo.set_user_language(str(chat_id), language)
            logger.info(f"Language {language} set for user {chat_id}")
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error setting language for user {chat_id}")
            raise StorageError(f"Failed to set language: {e}")

    async def get_user_data(self, chat_id: str) -> Dict:

        try:
            user_data = await self._user_repo.get_user_data(str(chat_id))
            return user_data or {}
        except Exception as e:
            logger.exception(f"Error getting user data {chat_id}")
            raise StorageError(f"Failed to get user data: {e}")

    async def delete_user_data(self, chat_id: str) -> bool:

        try:
            deleted = await self._user_repo.delete_user_data(str(chat_id))
            if deleted:
                logger.info(f"All data deleted for user {chat_id}")
            return deleted
        except Exception as e:
            logger.exception(f"Error deleting user data {chat_id}")
            raise StorageError(f"Failed to delete user data: {e}")
