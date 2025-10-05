from typing import Any, Callable, Dict, Type, Union

import httpx

from weatherbot.application.interfaces import (
    AdminApplicationServiceProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from weatherbot.domain.repositories import UserRepository
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager

OverrideValue = Union[Any, Callable[[], Any]]
OverrideMap = Dict[Type[Any], OverrideValue]


def _wrap(value: OverrideValue) -> OverrideValue:

    return value


def override_user_repository(value: OverrideValue) -> OverrideMap:

    return {UserRepository: _wrap(value)}


def override_weather_service(value: OverrideValue) -> OverrideMap:

    return {WeatherService: _wrap(value)}


def override_geocode_service(value: OverrideValue) -> OverrideMap:

    return {GeocodeService: _wrap(value)}


def override_http_client(value: OverrideValue) -> OverrideMap:

    return {httpx.AsyncClient: _wrap(value)}


def override_spam_protection_service(value: OverrideValue) -> OverrideMap:

    return {SpamProtectionService: _wrap(value)}


def override_weather_quota_manager(value: OverrideValue) -> OverrideMap:

    wrapped = _wrap(value)
    return {
        WeatherApiQuotaManager: wrapped,
        WeatherQuotaManagerProtocol: wrapped,
    }


def override_timezone_service(value: OverrideValue) -> OverrideMap:

    return {TimezoneService: _wrap(value)}


def override_user_service(value: Callable[[], Any]) -> OverrideMap:

    return {UserServiceProtocol: value}


def override_weather_application_service(value: Callable[[], Any]) -> OverrideMap:

    return {WeatherApplicationServiceProtocol: value}


def override_subscription_service(value: Callable[[], Any]) -> OverrideMap:

    return {SubscriptionServiceProtocol: value}


def override_admin_service(value: Callable[[], Any]) -> OverrideMap:

    return {AdminApplicationServiceProtocol: value}


def merge_overrides(*overrides: OverrideMap) -> OverrideMap:

    merged: OverrideMap = {}
    for mapping in overrides:
        merged.update(mapping)
    return merged
