from typing import Optional

from weatherbot.core.config import ConfigProvider, get_config_provider
from weatherbot.core.container import get_container


def register_config_provider(
    provider: Optional[ConfigProvider] = None,
) -> ConfigProvider:

    if provider is None:
        provider = get_config_provider()
    get_container().register_singleton(ConfigProvider, provider)
    return provider
