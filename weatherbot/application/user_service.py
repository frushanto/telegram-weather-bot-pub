import logging
from typing import Optional

from ..core.events import EventBus, UserLanguageChanged
from ..core.exceptions import StorageError, ValidationError
from ..domain.repositories import UserRepository
from ..domain.value_objects import UserHome, UserProfile
from .dtos import UserDataDTO

logger = logging.getLogger(__name__)


class UserService:

    def __init__(
        self,
        user_repository: UserRepository,
        timezone_service=None,
        event_bus: Optional[EventBus] = None,
    ):
        self._user_repo = user_repository
        self._timezone_service = timezone_service
        self._event_bus = event_bus

    async def get_user_home(self, chat_id: str) -> Optional[UserHome]:

        try:
            profile = await self.get_user_profile(chat_id)
            return profile.home
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

            profile = await self.get_user_profile(chat_id)
            home = UserHome(lat=lat, lon=lon, label=label.strip())

            # Automatically determine timezone if timezone_service is available
            if self._timezone_service:
                timezone_name = self._timezone_service.get_timezone_by_coordinates(
                    lat, lon
                )
                if timezone_name:
                    home = home.with_timezone(timezone_name)
                    logger.info(
                        f"Automatically set timezone '{timezone_name}' for user {chat_id}"
                    )
                else:
                    logger.warning(
                        f"Could not determine timezone for coordinates {lat:.4f}, {lon:.4f} for user {chat_id}"
                    )
            profile.home = home
            await self._user_repo.save_user_data(str(chat_id), profile.to_storage())
            logger.info(f"Home location set for user {chat_id}: {label}")
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error setting home location for user {chat_id}")
            raise StorageError(f"Failed to set home location: {e}")

    async def remove_user_home(self, chat_id: str) -> bool:

        try:
            profile = await self.get_user_profile(chat_id)
            if not profile.home:
                return False

            profile.home = None

            if profile.is_empty():
                await self._user_repo.delete_user_data(str(chat_id))
            else:
                await self._user_repo.save_user_data(str(chat_id), profile.to_storage())

            logger.info(f"Home location removed for user {chat_id}")
            return True
        except Exception as e:
            logger.exception(f"Error removing home location for user {chat_id}")
            raise StorageError(f"Failed to remove home location: {e}")

    async def get_user_language(self, chat_id: str) -> str:
        try:
            profile = await self.get_user_profile(chat_id)
            return profile.language or "ru"
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
            profile = await self.get_user_profile(chat_id)
            profile.language = language
            profile.language_explicit = True
            await self._user_repo.save_user_data(str(chat_id), profile.to_storage())
            logger.info(f"Language {language} set for user {chat_id}")

            # Publish event for language change
            if self._event_bus:
                event = UserLanguageChanged(chat_id=int(chat_id), lang=language)
                await self._event_bus.publish(event)
                logger.debug(f"Published UserLanguageChanged event for chat {chat_id}")
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error setting language for user {chat_id}")
            raise StorageError(f"Failed to set language: {e}")

    async def get_user_data(self, chat_id: str) -> UserDataDTO:

        try:
            profile = await self.get_user_profile(chat_id)
            return UserDataDTO.from_profile(profile)
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

    async def get_user_profile(self, chat_id: str) -> UserProfile:

        try:
            raw_data = await self._user_repo.get_user_data(str(chat_id)) or {}
            return UserProfile.from_storage(raw_data)
        except Exception as e:
            logger.exception(f"Error retrieving profile for user {chat_id}")
            raise StorageError(f"Failed to get user profile: {e}")
