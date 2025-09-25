from typing import Optional

from weatherbot.core.config import ConfigProvider, get_config_provider
from weatherbot.core.container import container


def register_config_provider(
    provider: Optional[ConfigProvider] = None,
) -> ConfigProvider:
    if provider is None:
        provider = get_config_provider()
    container.register_singleton(ConfigProvider, provider)
    return provider
