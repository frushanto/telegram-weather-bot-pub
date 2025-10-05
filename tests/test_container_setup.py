import asyncio
from pathlib import Path

import httpx
import pytest

from weatherbot.application.admin_service import AdminApplicationService
from weatherbot.application.interfaces import (
    AdminApplicationServiceProtocol,
    UserServiceProtocol,
    WeatherQuotaManagerProtocol,
)
from weatherbot.application.user_service import UserService
from weatherbot.core.config import (
    BotConfig,
    ConfigProvider,
    reset_config_provider,
    set_config,
)
from weatherbot.core.container import get_container
from weatherbot.core.exceptions import ConfigurationError
from weatherbot.domain.repositories import UserRepository
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.container import (
    merge_overrides,
    override_geocode_service,
    override_http_client,
    override_user_service,
    override_weather_quota_manager,
    override_weather_service,
    register_application_services,
    register_config_provider,
    register_external_clients,
    register_repositories,
)
from weatherbot.infrastructure.external_services import (
    NominatimGeocodeService,
    OpenMeteoWeatherService,
)
from weatherbot.infrastructure.json_repository import JsonUserRepository
from weatherbot.infrastructure.spam_protection import SpamProtection
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager


class DummyWeatherService(WeatherService):
    async def get_weather(self, lat: float, lon: float):  # type: ignore[override]
        return {"lat": lat, "lon": lon}


class DummyGeocodeService(GeocodeService):
    async def geocode_city(self, city: str):  # type: ignore[override]
        return (0.0, 0.0, city)


class DummyAsyncClient:
    closed: bool = False

    async def get(self, *args, **kwargs):
        raise NotImplementedError

    async def aclose(self) -> None:
        self.closed = True

    def close(self) -> None:
        self.closed = True


class StaticConfigProvider(ConfigProvider):
    def __init__(self, config: BotConfig) -> None:
        self._config = config

    def get(self) -> BotConfig:
        return self._config


@pytest.fixture
def sample_config(tmp_path: Path) -> BotConfig:
    cfg = BotConfig(
        token="test-token",
        admin_ids=[1],
        storage_path=str(tmp_path / "storage.json"),
        weather_api_quota_path=str(tmp_path / "quota.json"),
        weather_api_daily_limit=123,
    )
    return cfg


def test_register_config_provider_uses_current_provider(
    sample_config: BotConfig,
) -> None:
    set_config(sample_config)
    try:
        provider = register_config_provider()

        stored = get_container().get(ConfigProvider)
        assert stored is provider
        assert provider.get() is sample_config
    finally:
        reset_config_provider()


def test_register_config_provider_accepts_custom_provider(
    sample_config: BotConfig,
) -> None:
    provider = StaticConfigProvider(sample_config)
    returned = register_config_provider(provider)

    assert returned is provider
    assert get_container().get(ConfigProvider) is provider
    assert provider.get() is sample_config


def test_register_repositories_binds_json_user_repository(
    sample_config: BotConfig,
) -> None:
    register_repositories(sample_config)

    repo = get_container().get(UserRepository)
    assert isinstance(repo, JsonUserRepository)
    assert repo.storage_path == Path(sample_config.storage_path)


def test_register_external_clients_respects_config(sample_config: BotConfig) -> None:
    register_external_clients(sample_config)

    quota_manager = get_container().get(WeatherQuotaManagerProtocol)
    assert isinstance(quota_manager, WeatherApiQuotaManager)
    assert quota_manager._storage_path == Path(sample_config.weather_api_quota_path)
    assert quota_manager._max_requests_per_day == sample_config.weather_api_daily_limit

    container = get_container()
    client = container.get(httpx.AsyncClient)
    assert isinstance(client, httpx.AsyncClient)
    assert client.headers.get("User-Agent") == "WeatherBot/1.0"
    assert client.timeout.connect == 10.0

    assert container.get(WeatherApiQuotaManager) is quota_manager
    assert isinstance(container.get(GeocodeService), NominatimGeocodeService)
    assert isinstance(container.get(WeatherService), OpenMeteoWeatherService)
    weather_service = container.get(WeatherService)
    assert getattr(weather_service, "_http_client", None) is client
    assert isinstance(container.get(SpamProtectionService), SpamProtection)
    assert isinstance(container.get(TimezoneService), TimezoneService)

    asyncio.run(client.aclose())


def test_register_external_clients_invalid_provider(sample_config: BotConfig) -> None:
    sample_config.weather_service_provider = "unknown"

    with pytest.raises(ConfigurationError):
        register_external_clients(sample_config)


def test_register_external_clients_invalid_geocode(sample_config: BotConfig) -> None:
    sample_config.geocode_service_provider = "unknown"

    with pytest.raises(ConfigurationError):
        register_external_clients(sample_config)


def test_register_external_clients_overrides_services(sample_config: BotConfig) -> None:
    custom_quota = WeatherApiQuotaManager("ignored.json", 1)
    custom_client = DummyAsyncClient()
    overrides = merge_overrides(
        override_weather_quota_manager(custom_quota),
        override_weather_service(lambda: DummyWeatherService()),
        override_geocode_service(lambda: DummyGeocodeService()),
        override_http_client(custom_client),
    )

    register_external_clients(sample_config, overrides=overrides)

    container = get_container()
    assert container.get(WeatherQuotaManagerProtocol) is custom_quota
    assert container.get(WeatherApiQuotaManager) is custom_quota
    assert container.get(httpx.AsyncClient) is custom_client
    assert isinstance(container.get(WeatherService), DummyWeatherService)
    assert isinstance(container.get(GeocodeService), DummyGeocodeService)


def test_register_application_services_wires_factories(
    sample_config: BotConfig,
) -> None:
    set_config(sample_config)
    try:
        provider = register_config_provider()
        register_repositories(sample_config)
        register_external_clients(sample_config)

        register_application_services(provider)

        user_service = get_container().get(UserServiceProtocol)
        assert isinstance(user_service, UserService)

        admin_service = get_container().get(AdminApplicationServiceProtocol)
        assert admin_service._config_provider is provider  # type: ignore[attr-defined]
    finally:
        reset_config_provider()


def test_register_application_services_accepts_overrides(
    sample_config: BotConfig,
) -> None:
    set_config(sample_config)
    try:
        provider = register_config_provider()
        register_repositories(sample_config)
        register_external_clients(sample_config)

        class StubUserService:
            pass

        overrides = override_user_service(lambda: StubUserService())
        register_application_services(provider, overrides=overrides)

        resolved = get_container().get(UserServiceProtocol)
        assert isinstance(resolved, StubUserService)
    finally:
        reset_config_provider()
