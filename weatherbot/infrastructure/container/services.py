from typing import Any, Callable, Dict, Optional, Type

from weatherbot.application.admin_service import AdminApplicationService
from weatherbot.application.interfaces import (
    AdminApplicationServiceProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.application.weather_service import WeatherApplicationService
from weatherbot.core.config import ConfigProvider
from weatherbot.core.container import get_container
from weatherbot.core.events import EventBus
from weatherbot.domain.repositories import UserRepository
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.jobs.backup import perform_backup


def _register_factory(
    interface: Type[Any],
    overrides: Optional[Dict[Type[Any], Callable[[], Any]]],
    factory: Callable[[], Any],
) -> None:

    container = get_container()

    if overrides and interface in overrides:
        override_factory = overrides[interface]
        if not callable(override_factory):
            raise TypeError(f"Override for {interface.__name__} must be callable")
        container.register_factory(interface, override_factory)
    else:
        container.register_factory(interface, factory)


def register_application_services(
    config_provider: ConfigProvider,
    overrides: Optional[Dict[Type[Any], Callable[[], Any]]] = None,
) -> None:

    container = get_container()

    _register_factory(
        UserServiceProtocol,
        overrides,
        lambda: UserService(
            container.get(UserRepository),
            container.get(TimezoneService),
            container.get(EventBus),
        ),
    )
    _register_factory(
        WeatherApplicationServiceProtocol,
        overrides,
        lambda: WeatherApplicationService(
            container.get(WeatherService), container.get(GeocodeService)
        ),
    )
    _register_factory(
        SubscriptionServiceProtocol,
        overrides,
        lambda: SubscriptionService(container.get(UserRepository)),
    )
    _register_factory(
        AdminApplicationServiceProtocol,
        overrides,
        lambda: AdminApplicationService(
            container.get(SpamProtectionService),
            container.get(SubscriptionServiceProtocol),
            container.get(WeatherApplicationServiceProtocol),
            container.get(WeatherQuotaManagerProtocol),
            perform_backup,
            config_provider,
        ),
    )
