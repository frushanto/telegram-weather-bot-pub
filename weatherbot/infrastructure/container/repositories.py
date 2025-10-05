from typing import Any, Callable, Dict, Optional, Type, Union

from weatherbot.core.config import BotConfig
from weatherbot.core.container import get_container
from weatherbot.domain.repositories import UserRepository
from weatherbot.infrastructure.json_repository import JsonUserRepository

OverrideValue = Union[Any, Callable[[], Any]]


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


def register_repositories(
    config: BotConfig,
    overrides: Optional[Dict[Type[Any], OverrideValue]] = None,
) -> None:
    _register_singleton(
        UserRepository,
        overrides,
        lambda: JsonUserRepository(config.storage_path),
    )
