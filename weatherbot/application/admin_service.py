from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, List, Optional

from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.weather_service import WeatherApplicationService
from weatherbot.core.config import ConfigProvider
from weatherbot.domain.weather import WeatherReport
from weatherbot.infrastructure.spam_protection import SpamProtection
from weatherbot.infrastructure.weather_quota import (
    WeatherApiQuotaManager,
    WeatherQuotaStatus,
)


@dataclass
class AdminTopUser:
    user_id: str | int
    daily_requests: int
    is_blocked: bool


@dataclass
class AdminStatsResult:
    user_count: int
    blocked_count: int
    top_users: List[AdminTopUser]


@dataclass
class AdminUserInfo:
    requests_today: int
    is_blocked: bool
    block_count: int
    blocked_until: Optional[datetime]


@dataclass
class AdminSubscriptionEntry:
    chat_id: str
    hour: int
    minute: int
    label: Optional[str]
    timezone: Optional[str]


@dataclass
class AdminSubscriptionsResult:
    total: int
    items: List[AdminSubscriptionEntry]


@dataclass
class AdminConfigSnapshot:
    timezone: str
    storage_path: str
    backup_enabled: bool
    backup_hour: int
    backup_retention_days: int
    spam_limits: tuple[int, int, int]


@dataclass
class AdminTestWeatherResult:
    place_label: str
    weather_data: WeatherReport


class AdminApplicationService:
    def __init__(
        self,
        spam_protection: SpamProtection,
        subscription_service: SubscriptionService,
        weather_service: WeatherApplicationService,
        quota_manager: WeatherApiQuotaManager,
        backup_runner: Callable[[], object],
        config_provider: ConfigProvider,
    ) -> None:
        self._spam_protection = spam_protection
        self._subscription_service = subscription_service
        self._weather_service = weather_service
        self._quota_manager = quota_manager
        self._backup_runner = backup_runner
        self._config_provider = config_provider

    async def get_stats(self) -> AdminStatsResult:
        activities = self._spam_protection.user_activities
        blocked_users: Iterable[int] = self._spam_protection.blocked_users
        blocked_lookup = {self._to_int(user_id) for user_id in blocked_users}

        top_users: List[AdminTopUser] = []
        for raw_user_id, activity in activities.items():
            user_id = raw_user_id
            try:
                normalized_id = self._to_int(raw_user_id)
            except (TypeError, ValueError):
                normalized_id = raw_user_id
            top_users.append(
                AdminTopUser(
                    user_id=user_id,
                    daily_requests=getattr(activity, "daily_requests", 0),
                    is_blocked=normalized_id in blocked_lookup,
                )
            )

        top_users.sort(key=lambda item: item.daily_requests, reverse=True)
        top_users = top_users[:10]

        return AdminStatsResult(
            user_count=len(activities),
            blocked_count=len(self._spam_protection.blocked_users),
            top_users=top_users,
        )

    async def unblock_user(self, user_id: int) -> bool:
        return await self._spam_protection.unblock_user(user_id)

    async def get_user_info(self, user_id: int) -> AdminUserInfo:
        stats = self._spam_protection.get_user_stats(user_id)
        blocked_until_ts = stats.get("blocked_until")
        blocked_until_dt: Optional[datetime] = None
        if blocked_until_ts:
            blocked_until_dt = datetime.fromtimestamp(blocked_until_ts, tz=timezone.utc)
        return AdminUserInfo(
            requests_today=int(stats.get("requests_today", 0)),
            is_blocked=bool(stats.get("is_blocked", False)),
            block_count=int(stats.get("block_count", 0)),
            blocked_until=blocked_until_dt,
        )

    async def cleanup_spam(self) -> None:
        await self._spam_protection.cleanup_old_data()

    async def run_manual_backup(self) -> None:
        await self._backup_runner()

    async def list_subscriptions(self) -> AdminSubscriptionsResult:
        subscriptions = await self._subscription_service.get_all_subscriptions()
        items: List[AdminSubscriptionEntry] = []
        for entry in subscriptions:
            home = entry.home
            items.append(
                AdminSubscriptionEntry(
                    chat_id=entry.chat_id,
                    hour=entry.subscription.hour,
                    minute=entry.subscription.minute,
                    label=home.label if home else None,
                    timezone=home.timezone if home else None,
                )
            )
        items.sort(key=lambda entry: (entry.hour, entry.minute, entry.chat_id))
        return AdminSubscriptionsResult(total=len(items), items=items)

    async def get_runtime_config(self) -> AdminConfigSnapshot:
        config = self._config_provider.get()
        spam_config = config.spam_config
        return AdminConfigSnapshot(
            timezone=str(config.timezone),
            storage_path=config.storage_path,
            backup_enabled=config.backup_enabled,
            backup_hour=config.backup_time_hour,
            backup_retention_days=config.backup_retention_days,
            spam_limits=(
                spam_config.max_requests_per_minute,
                spam_config.max_requests_per_hour,
                spam_config.max_requests_per_day,
            ),
        )

    async def test_weather(self, city: str) -> AdminTestWeatherResult:
        weather_data, label = await self._weather_service.get_weather_by_city(city)
        place = label or city
        return AdminTestWeatherResult(place_label=place, weather_data=weather_data)

    async def get_quota_status(self) -> WeatherQuotaStatus:
        return await self._quota_manager.get_status()

    @staticmethod
    def _to_int(value) -> int:
        if isinstance(value, int):
            return value
        return int(value)
