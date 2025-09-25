from pathlib import Path

import pytest

from weatherbot.application.admin_service import AdminApplicationService
from weatherbot.application.user_service import UserService
from weatherbot.core.config import (
    BotConfig,
    ConfigProvider,
    reset_config_provider,
    set_config,
)
from weatherbot.core.container import container
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
from weatherbot.infrastructure.spam_service import LegacySpamProtectionService
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager


class DummyWeatherService(WeatherService):
    async def get_weather(self, lat: float, lon: float):  # type: ignore[override]
        return {"lat": lat, "lon": lon}


class DummyGeocodeService(GeocodeService):
    async def geocode_city(self, city: str):  # type: ignore[override]
        return (0.0, 0.0, city)


class StaticConfigProvider(ConfigProvider):
    def __init__(self, config: BotConfig) -> None:
        self._config = config

    def get(self) -> BotConfig:
        return self._config


@pytest.fixture(autouse=True)
def clean_container():
    container.clear()
    yield
    container.clear()


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

        stored = container.get(ConfigProvider)
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
    assert container.get(ConfigProvider) is provider
    assert provider.get() is sample_config


def test_register_repositories_binds_json_user_repository(
    sample_config: BotConfig,
) -> None:
    register_repositories(sample_config)

    repo = container.get(UserRepository)
    assert isinstance(repo, JsonUserRepository)
    assert repo.storage_path == Path(sample_config.storage_path)


def test_register_external_clients_respects_config(sample_config: BotConfig) -> None:
    register_external_clients(sample_config)

    quota_manager = container.get(WeatherApiQuotaManager)
    assert quota_manager._storage_path == Path(sample_config.weather_api_quota_path)
    assert quota_manager._max_requests_per_day == sample_config.weather_api_daily_limit

    assert isinstance(container.get(GeocodeService), NominatimGeocodeService)
    assert isinstance(container.get(WeatherService), OpenMeteoWeatherService)
    assert isinstance(container.get(SpamProtectionService), LegacySpamProtectionService)
    assert isinstance(container.get(TimezoneService), TimezoneService)


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
    overrides = merge_overrides(
        override_weather_quota_manager(custom_quota),
        override_weather_service(lambda: DummyWeatherService()),
        override_geocode_service(lambda: DummyGeocodeService()),
    )

    register_external_clients(sample_config, overrides=overrides)

    assert container.get(WeatherApiQuotaManager) is custom_quota
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

        user_service = container.get(UserService)
        assert isinstance(user_service, UserService)

        admin_service = container.get(AdminApplicationService)
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

        resolved = container.get(UserService)
        assert isinstance(resolved, StubUserService)
    finally:
        reset_config_provider()
