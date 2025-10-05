"""Protocol interfaces for core application services."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Iterable, Optional, Protocol, Tuple

from weatherbot.application.dtos import (
    CityWeatherDTO,
    GeocodeResultDTO,
    SubscriptionScheduleMap,
    UserDataDTO,
)
from weatherbot.domain.conversation import (
    ConversationMode,
    ConversationState,
    ConversationStateManager,
)
from weatherbot.domain.value_objects import SubscriptionEntry, UserHome, UserProfile
from weatherbot.domain.weather import WeatherReport

if TYPE_CHECKING:  # pragma: no cover - typing only
    from weatherbot.application.admin_service import (
        AdminConfigSnapshot,
        AdminQuotaStatus,
        AdminStatsResult,
        AdminSubscriptionsResult,
        AdminTestWeatherResult,
        AdminUserInfo,
    )
    from weatherbot.domain.value_objects import UserSubscription
    from weatherbot.infrastructure.weather_quota import WeatherQuotaStatus
else:  # pragma: no cover - runtime fallbacks
    AdminConfigSnapshot = AdminStatsResult = AdminSubscriptionsResult = Any  # type: ignore
    AdminQuotaStatus = Any  # type: ignore
    AdminTestWeatherResult = AdminUserInfo = Any  # type: ignore
    UserSubscription = Any  # type: ignore
    WeatherQuotaStatus = Any  # type: ignore


class UserServiceProtocol(Protocol):

    async def get_user_home(self, chat_id: str) -> Optional[UserHome]: ...

    async def set_user_home(
        self, chat_id: str, lat: float, lon: float, label: str
    ) -> None: ...

    async def remove_user_home(self, chat_id: str) -> bool: ...

    async def get_user_language(self, chat_id: str) -> str: ...

    async def set_user_language(self, chat_id: str, language: str) -> None: ...

    async def get_user_data(self, chat_id: str) -> UserDataDTO: ...

    async def delete_user_data(self, chat_id: str) -> bool: ...

    async def get_user_profile(self, chat_id: str) -> UserProfile: ...


class WeatherApplicationServiceProtocol(Protocol):

    async def get_weather_by_coordinates(
        self, lat: float, lon: float
    ) -> WeatherReport: ...

    async def get_weather_by_city(self, city: str) -> CityWeatherDTO: ...

    async def geocode_city(self, city: str) -> Optional[GeocodeResultDTO]: ...


class SubscriptionServiceProtocol(Protocol):

    async def set_subscription(
        self, chat_id: str, hour: int, minute: int = 0
    ) -> None: ...

    async def remove_subscription(self, chat_id: str) -> bool: ...

    async def get_subscription(self, chat_id: str) -> Optional[UserSubscription]: ...

    async def get_all_subscriptions(self) -> Iterable[SubscriptionEntry]: ...

    async def get_all_subscriptions_dict(self) -> SubscriptionScheduleMap: ...

    async def parse_time_string(self, time_str: str) -> Tuple[int, int]: ...


class WeatherQuotaManagerProtocol(Protocol):

    async def get_status(
        self, now: Optional[datetime] = None
    ) -> WeatherQuotaStatus: ...

    async def mark_alert_sent(
        self, threshold: float, reset_at: Optional[datetime]
    ) -> None: ...


class AdminApplicationServiceProtocol(Protocol):

    async def get_stats(self) -> AdminStatsResult: ...

    async def unblock_user(self, user_id: int) -> bool: ...

    async def get_user_info(self, user_id: int) -> AdminUserInfo: ...

    async def cleanup_spam(self) -> None: ...

    async def run_manual_backup(self) -> None: ...

    async def list_subscriptions(self) -> AdminSubscriptionsResult: ...

    async def get_runtime_config(self) -> AdminConfigSnapshot: ...

    async def test_weather(self, city: str) -> AdminTestWeatherResult: ...

    async def get_quota_status(self) -> AdminQuotaStatus: ...


class ConversationStateStoreProtocol(Protocol):

    conversation_manager: ConversationStateManager

    def get_state(self, chat_id: int) -> ConversationState: ...

    def set_state(self, chat_id: int, state: ConversationState) -> None: ...

    def set_awaiting_mode(self, chat_id: int, mode: ConversationMode) -> None: ...

    def set_location(self, chat_id: int, lat: float, lon: float) -> None: ...

    def clear_conversation(self, chat_id: int) -> None: ...

    def is_awaiting(self, chat_id: int, mode: ConversationMode) -> bool: ...

    def get_last_location(self, chat_id: int) -> Optional[Tuple[float, float]]: ...

    def reset(self) -> None: ...
