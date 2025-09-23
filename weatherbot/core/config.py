import os
from dataclasses import dataclass, field
from typing import List
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

        return cls(
            token=token,
            admin_ids=admin_ids,
            admin_language=admin_language,
            spam_config=spam_config,
            storage_path=storage_path,
            backup_enabled=backup_enabled,
            backup_retention_days=backup_retention_days,
            backup_time_hour=backup_time_hour,
        )


_config: BotConfig = None


def get_config() -> BotConfig:

    global _config
    if _config is None:
        _config = BotConfig.from_env()
    return _config


def set_config(config_instance: BotConfig) -> None:

    global _config
    _config = config_instance
