import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .exceptions import ConfigurationError

load_dotenv()


@dataclass
class SpamConfig:

    max_requests_per_minute: int = 30
    max_requests_per_hour: int = 200
    max_requests_per_day: int = 300
    block_duration: int = 300
    extended_block_duration: int = 3600
    min_cooldown: float = 1.0
    max_message_length: int = 1000


@dataclass
class BotConfig:

    token: str
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Europe/Berlin"))
    admin_ids: List[int] = field(default_factory=list)
    admin_language: str = "ru"
    spam_config: SpamConfig = field(default_factory=SpamConfig)
    storage_path: str = "data/storage.json"
    backup_enabled: bool = True
    backup_retention_days: int = 30
    backup_time_hour: int = 3
    weather_api_daily_limit: int = 1000
    weather_api_quota_path: str = "data/weather_api_quota.json"
    weather_service_provider: str = "open-meteo"
    geocode_service_provider: str = "nominatim"
    metrics_host: str = "127.0.0.1"
    metrics_port: int = 9000
    health_host: str = "127.0.0.1"
    health_port: int = 9001
    schedule_weather_retry_attempts: int = 3
    schedule_weather_retry_delay_sec: int = 5

    @classmethod
    def from_env(cls) -> "BotConfig":

        token = os.getenv("BOT_TOKEN") or ""
        if not token:

            import logging

            logging.getLogger(__name__).warning(
                "BOT_TOKEN not set; using empty token (test mode)"
            )

        admin_ids = []
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            try:
                admin_ids = [
                    int(id_str.strip())
                    for id_str in admin_ids_str.split(",")
                    if id_str.strip()
                ]
            except ValueError:
                raise ConfigurationError("Invalid ADMIN_IDS format in .env file")

        spam_config = SpamConfig(
            max_requests_per_minute=int(
                os.getenv("SPAM_MAX_REQUESTS_PER_MINUTE", "30")
            ),
            max_requests_per_hour=int(os.getenv("SPAM_MAX_REQUESTS_PER_HOUR", "200")),
            max_requests_per_day=int(os.getenv("SPAM_MAX_REQUESTS_PER_DAY", "300")),
            block_duration=int(os.getenv("SPAM_BLOCK_DURATION", "300")),
            extended_block_duration=int(
                os.getenv("SPAM_EXTENDED_BLOCK_DURATION", "3600")
            ),
            min_cooldown=float(os.getenv("SPAM_MIN_COOLDOWN", "1")),
            max_message_length=int(os.getenv("SPAM_MAX_MESSAGE_LENGTH", "1000")),
        )

        admin_language = os.getenv("ADMIN_LANGUAGE", "ru")
        storage_path = os.getenv("STORAGE_PATH", "data/storage.json")
        backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        backup_time_hour = int(os.getenv("BACKUP_TIME_HOUR", "3"))
        weather_api_daily_limit = int(os.getenv("WEATHER_API_DAILY_LIMIT", "1000"))
        weather_api_quota_path = os.getenv(
            "WEATHER_API_QUOTA_PATH", "data/weather_api_quota.json"
        )
        weather_service_provider = os.getenv(
            "WEATHER_SERVICE_PROVIDER", "open-meteo"
        ).lower()
        geocode_service_provider = os.getenv(
            "GEOCODE_SERVICE_PROVIDER", "nominatim"
        ).lower()
        metrics_host = os.getenv("METRICS_HOST", "127.0.0.1")
        metrics_port = int(os.getenv("METRICS_PORT", "9000"))
        health_host = os.getenv("HEALTH_HOST", "127.0.0.1")
        health_port = int(os.getenv("HEALTH_PORT", "9001"))
        schedule_weather_retry_attempts = int(
            os.getenv("SCHEDULE_WEATHER_RETRY_ATTEMPTS", "3")
        )
        schedule_weather_retry_delay_sec = int(
            os.getenv("SCHEDULE_WEATHER_RETRY_DELAY_SEC", "5")
        )

        return cls(
            token=token,
            admin_ids=admin_ids,
            admin_language=admin_language,
            spam_config=spam_config,
            storage_path=storage_path,
            backup_enabled=backup_enabled,
            backup_retention_days=backup_retention_days,
            backup_time_hour=backup_time_hour,
            weather_api_daily_limit=weather_api_daily_limit,
            weather_api_quota_path=weather_api_quota_path,
            weather_service_provider=weather_service_provider,
            geocode_service_provider=geocode_service_provider,
            metrics_host=metrics_host,
            metrics_port=metrics_port,
            health_host=health_host,
            health_port=health_port,
            schedule_weather_retry_attempts=schedule_weather_retry_attempts,
            schedule_weather_retry_delay_sec=schedule_weather_retry_delay_sec,
        )


class ConfigProvider(ABC):

    @abstractmethod
    def get(self) -> BotConfig:

        raise NotImplementedError


class EnvConfigProvider(ConfigProvider):

    def __init__(self) -> None:

        self._config: Optional[BotConfig] = None

    def get(self) -> BotConfig:

        if self._config is None:
            self._config = BotConfig.from_env()
        return self._config

    def reset(self) -> None:

        self._config = None


class StaticConfigProvider(ConfigProvider):

    def __init__(self, config: BotConfig) -> None:

        self._config = config

    def get(self) -> BotConfig:

        return self._config


_config_provider: ConfigProvider = EnvConfigProvider()


def get_config_provider() -> ConfigProvider:

    return _config_provider


def set_config_provider(provider: ConfigProvider) -> None:

    global _config_provider
    _config_provider = provider


def reset_config_provider() -> None:

    set_config_provider(EnvConfigProvider())


def get_config() -> BotConfig:

    return _config_provider.get()


def set_config(config_instance: BotConfig) -> None:

    set_config_provider(StaticConfigProvider(config_instance))
