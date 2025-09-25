from typing import Any, Callable, Dict, Optional, Type

from weatherbot.application.admin_service import AdminApplicationService
from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.application.weather_service import WeatherApplicationService
from weatherbot.core.config import ConfigProvider
from weatherbot.core.container import container
from weatherbot.domain.repositories import UserRepository
from weatherbot.domain.services import GeocodeService, WeatherService
from weatherbot.infrastructure.spam_protection import spam_protection
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager
from weatherbot.jobs.backup import perform_backup


def _register_factory(
    interface: Type[Any],
    overrides: Optional[Dict[Type[Any], Callable[[], Any]]],
    factory: Callable[[], Any],
) -> None:
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
    _register_factory(
        UserService,
        overrides,
        lambda: UserService(
            container.get(UserRepository), container.get(TimezoneService)
        ),
    )
    _register_factory(
        WeatherApplicationService,
        overrides,
        lambda: WeatherApplicationService(
            container.get(WeatherService), container.get(GeocodeService)
        ),
    )
    _register_factory(
        SubscriptionService,
        overrides,
        lambda: SubscriptionService(container.get(UserRepository)),
    )
    _register_factory(
        AdminApplicationService,
        overrides,
        lambda: AdminApplicationService(
            spam_protection,
            container.get(SubscriptionService),
            container.get(WeatherApplicationService),
            container.get(WeatherApiQuotaManager),
            perform_backup,
            config_provider,
        ),
    )
