from ..application.subscription_service import SubscriptionService
from ..application.user_service import UserService
from ..application.weather_service import WeatherApplicationService
from ..core.config import get_config
from ..core.container import container
from ..domain.repositories import UserRepository
from ..domain.services import GeocodeService, SpamProtectionService, WeatherService
from .external_services import NominatimGeocodeService, OpenMeteoWeatherService
from .json_repository import JsonUserRepository
from .spam_service import LegacySpamProtectionService
from .timezone_service import TimezoneService


def setup_container() -> None:

    config = get_config()
    container.register_singleton(
        UserRepository, JsonUserRepository(config.storage_path)
    )

    container.register_singleton(WeatherService, OpenMeteoWeatherService())
    container.register_singleton(GeocodeService, NominatimGeocodeService())
    container.register_singleton(SpamProtectionService, LegacySpamProtectionService())
    container.register_singleton(TimezoneService, TimezoneService())

    container.register_factory(
        UserService,
        lambda: UserService(
            container.get(UserRepository), container.get(TimezoneService)
        ),
    )
    container.register_factory(
        WeatherApplicationService,
        lambda: WeatherApplicationService(
            container.get(WeatherService), container.get(GeocodeService)
        ),
    )
    container.register_factory(
        SubscriptionService, lambda: SubscriptionService(container.get(UserRepository))
    )


def get_user_repository() -> UserRepository:

    return container.get(UserRepository)


def get_weather_service() -> WeatherService:

    return container.get(WeatherService)


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
