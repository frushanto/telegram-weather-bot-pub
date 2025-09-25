from typing import Dict, Type

from ..application.admin_service import AdminApplicationService
from ..application.subscription_service import SubscriptionService
from ..application.user_service import UserService
from ..application.weather_service import WeatherApplicationService
from ..core.config import ConfigProvider
from ..core.container import container
from ..domain.repositories import UserRepository
from ..domain.services import GeocodeService, SpamProtectionService, WeatherService
from .container import (
    register_application_services,
    register_config_provider,
    register_external_clients,
    register_repositories,
)
from .timezone_service import TimezoneService
from .weather_quota import WeatherApiQuotaManager


def setup_container() -> None:
    config_provider: ConfigProvider = register_config_provider()
    config = config_provider.get()
    register_repositories(config)
    register_external_clients(config)
    register_application_services(config_provider)


def override_dependencies(overrides: Dict[Type, object]) -> None:
    for interface, instance in overrides.items():
        container.register_instance(interface, instance)


def get_user_repository() -> UserRepository:
    return container.get(UserRepository)


def get_weather_service() -> WeatherService:
    return container.get(WeatherService)


def get_weather_quota_manager() -> WeatherApiQuotaManager:
    return container.get(WeatherApiQuotaManager)


def get_geocode_service() -> GeocodeService:
    return container.get(GeocodeService)


def get_spam_protection_service() -> SpamProtectionService:
    return container.get(SpamProtectionService)


def get_user_service() -> UserService:
    return container.get(UserService)


def get_weather_application_service() -> WeatherApplicationService:
    return container.get(WeatherApplicationService)


def get_subscription_service() -> SubscriptionService:
    return container.get(SubscriptionService)


def get_timezone_service() -> TimezoneService:
    return container.get(TimezoneService)


def get_admin_service() -> AdminApplicationService:
    return container.get(AdminApplicationService)
