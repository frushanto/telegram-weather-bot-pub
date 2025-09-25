"""Helpers for modular DI container setup."""

from .config import register_config_provider
from .external_clients import register_external_clients
from .overrides import (
    merge_overrides,
    override_admin_service,
    override_geocode_service,
    override_spam_protection_service,
    override_subscription_service,
    override_timezone_service,
    override_user_repository,
    override_user_service,
    override_weather_application_service,
    override_weather_quota_manager,
    override_weather_service,
)
from .repositories import register_repositories
from .services import register_application_services

__all__ = [
    "register_config_provider",
    "register_repositories",
    "register_external_clients",
    "register_application_services",
    "override_user_repository",
    "override_weather_service",
    "override_geocode_service",
    "override_spam_protection_service",
    "override_weather_quota_manager",
    "override_timezone_service",
    "override_user_service",
    "override_weather_application_service",
    "override_subscription_service",
    "override_admin_service",
    "merge_overrides",
]
