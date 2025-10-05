from typing import Any, Callable, Dict, Optional, Type, Union

import httpx

from weatherbot.application.interfaces import WeatherQuotaManagerProtocol
from weatherbot.core.config import BotConfig
from weatherbot.core.container import get_container
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.external_services import (
    create_geocode_service,
    create_weather_service,
)
from weatherbot.infrastructure.spam_protection import SpamProtection
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager

OverrideValue = Union[Any, Callable[[], Any]]

HTTP_CLIENT_TIMEOUT = 10.0


def _register_singleton(
    interface: Type[Any],
    overrides: Optional[Dict[Type[Any], OverrideValue]],
    factory: Callable[[], Any],
) -> Any:
    value: Any
    container = get_container()

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
    http_client = _register_singleton(
        httpx.AsyncClient,
        overrides,
        lambda: httpx.AsyncClient(
            timeout=httpx.Timeout(HTTP_CLIENT_TIMEOUT),
            headers={"User-Agent": "WeatherBot/1.0"},
        ),
    )

    quota_manager = _register_singleton(
        WeatherApiQuotaManager,
        overrides,
        lambda: WeatherApiQuotaManager(
            storage_path=config.weather_api_quota_path,
            max_requests_per_day=config.weather_api_daily_limit,
        ),
    )

    container = get_container()
    if (
        overrides
        and WeatherQuotaManagerProtocol in overrides
        and WeatherApiQuotaManager not in overrides
    ):
        override = overrides[WeatherQuotaManagerProtocol]
        quota_protocol = override() if callable(override) else override
    else:
        quota_protocol = quota_manager
    container.register_singleton(WeatherQuotaManagerProtocol, quota_protocol)

    _register_singleton(
        WeatherService,
        overrides,
        lambda: create_weather_service(
            config.weather_service_provider, quota_manager, http_client
        ),
    )
    _register_singleton(
        GeocodeService,
        overrides,
        lambda: create_geocode_service(config.geocode_service_provider, http_client),
    )
    _register_singleton(
        SpamProtectionService,
        overrides,
        lambda: SpamProtection(),
    )
    _register_singleton(
        TimezoneService,
        overrides,
        TimezoneService,
    )
