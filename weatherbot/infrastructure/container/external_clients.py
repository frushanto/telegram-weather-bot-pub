from typing import Any, Callable, Dict, Optional, Type, Union

from weatherbot.core.config import BotConfig
from weatherbot.core.container import container
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.external_services import (
    create_geocode_service,
    create_weather_service,
)
from weatherbot.infrastructure.spam_service import LegacySpamProtectionService
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager

OverrideValue = Union[Any, Callable[[], Any]]


def _register_singleton(
    interface: Type[Any],
    overrides: Optional[Dict[Type[Any], OverrideValue]],
    factory: Callable[[], Any],
) -> Any:
    value: Any
    if overrides and interface in overrides:
        override = overrides[interface]
        value = override() if callable(override) else override
    else:
        value = factory()
    container.register_singleton(interface, value)
    return value


def register_external_clients(
    config: BotConfig,
    overrides: Optional[Dict[Type[Any], OverrideValue]] = None,
) -> None:
    quota_manager = _register_singleton(
        WeatherApiQuotaManager,
        overrides,
        lambda: WeatherApiQuotaManager(
            storage_path=config.weather_api_quota_path,
            max_requests_per_day=config.weather_api_daily_limit,
        ),
    )

    _register_singleton(
        WeatherService,
        overrides,
        lambda: create_weather_service(config.weather_service_provider, quota_manager),
    )
    _register_singleton(
        GeocodeService,
        overrides,
        lambda: create_geocode_service(config.geocode_service_provider),
    )
    _register_singleton(
        SpamProtectionService,
        overrides,
        LegacySpamProtectionService,
    )
    _register_singleton(
        TimezoneService,
        overrides,
        TimezoneService,
    )
