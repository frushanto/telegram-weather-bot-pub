"""Convenience helpers for building DI override dictionaries."""

from typing import Any, Callable, Dict, Type, Union

from weatherbot.application.admin_service import AdminApplicationService
from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.application.weather_service import WeatherApplicationService
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


def override_spam_protection_service(value: OverrideValue) -> OverrideMap:
    return {SpamProtectionService: _wrap(value)}


def override_weather_quota_manager(value: OverrideValue) -> OverrideMap:
    return {WeatherApiQuotaManager: _wrap(value)}


def override_timezone_service(value: OverrideValue) -> OverrideMap:
    return {TimezoneService: _wrap(value)}


def override_user_service(value: Callable[[], Any]) -> OverrideMap:
    return {UserService: value}


def override_weather_application_service(value: Callable[[], Any]) -> OverrideMap:
    return {WeatherApplicationService: value}


def override_subscription_service(value: Callable[[], Any]) -> OverrideMap:
    return {SubscriptionService: value}


def override_admin_service(value: Callable[[], Any]) -> OverrideMap:
    return {AdminApplicationService: value}


def merge_overrides(*overrides: OverrideMap) -> OverrideMap:
    merged: OverrideMap = {}
    for mapping in overrides:
        merged.update(mapping)
    return merged
