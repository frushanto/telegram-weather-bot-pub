from typing import Dict, Type

from ..application.interfaces import (
    AdminApplicationServiceProtocol,
    ConversationStateStoreProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from ..core.config import ConfigProvider
from ..core.container import Container, get_container, set_container
from ..core.decorators import configure_decorators
from ..core.events import EventBus, Mediator
from ..domain.repositories import UserRepository
from ..domain.services import GeocodeService, SpamProtectionService, WeatherService
from ..presentation.i18n import Localization, i18n
from ..presentation.subscription_presenter import SubscriptionPresenter
from .container import (
    register_application_services,
    register_config_provider,
    register_external_clients,
    register_repositories,
)
from .state import ConversationStateStore
from .timezone_service import TimezoneService


def setup_container() -> Container:
    """Create and populate the global dependency injection container."""
    container = Container()
    set_container(container)

    config_provider: ConfigProvider = register_config_provider()
    config = config_provider.get()
    register_repositories(config)
    register_external_clients(config)
    register_application_services(config_provider)

    container.register_singleton(Localization, Localization())
    container.register_singleton(EventBus, EventBus())
    container.register_singleton(Mediator, Mediator())

    try:
        state_store = container.get(ConversationStateStore)
    except ValueError:
        state_store = ConversationStateStore()
        container.register_singleton(ConversationStateStore, state_store)
    container.register_singleton(ConversationStateStoreProtocol, state_store)

    async def _resolve_user_language(user_id: int) -> str:

        user_service = container.get(UserServiceProtocol)
        return await user_service.get_user_language(str(user_id))

    configure_decorators(
        spam_service_provider=lambda: container.get(SpamProtectionService),
        user_language_resolver=_resolve_user_language,
        translator=lambda key, lang, **kwargs: container.get(Localization).get(
            key, lang, **kwargs
        ),
        default_language=config.admin_language or "ru",
    )

    return container


def override_dependencies(overrides: Dict[Type, object]) -> None:
    """Allow tests and jobs to override container-managed dependencies."""
    container = get_container()
    for interface, instance in overrides.items():
        container.register_instance(interface, instance)


def get_user_repository() -> UserRepository:

    return get_container().get(UserRepository)


def get_weather_service() -> WeatherService:

    return get_container().get(WeatherService)


def get_weather_quota_manager() -> WeatherQuotaManagerProtocol:

    return get_container().get(WeatherQuotaManagerProtocol)


def get_geocode_service() -> GeocodeService:

    return get_container().get(GeocodeService)


def get_spam_protection_service() -> SpamProtectionService:

    return get_container().get(SpamProtectionService)


def get_user_service() -> UserServiceProtocol:

    return get_container().get(UserServiceProtocol)


def get_weather_application_service() -> WeatherApplicationServiceProtocol:

    return get_container().get(WeatherApplicationServiceProtocol)


def get_subscription_service() -> SubscriptionServiceProtocol:

    return get_container().get(SubscriptionServiceProtocol)


def create_subscription_presenter() -> SubscriptionPresenter:

    return SubscriptionPresenter(
        get_subscription_service(),
        get_user_service(),
        i18n.get,
        get_conversation_state_store(),
    )


def get_timezone_service() -> TimezoneService:

    return get_container().get(TimezoneService)


def get_admin_service() -> AdminApplicationServiceProtocol:

    return get_container().get(AdminApplicationServiceProtocol)


def get_conversation_state_store() -> ConversationStateStoreProtocol:

    container = get_container()
    try:
        store = container.get(ConversationStateStore)
    except ValueError:
        store = ConversationStateStore()
        container.register_singleton(ConversationStateStore, store)
    container.register_singleton(ConversationStateStoreProtocol, store)
    return store
