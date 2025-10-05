import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from weatherbot.application.dtos import GeocodeResultDTO
from weatherbot.application.interfaces import ConversationStateStoreProtocol
from weatherbot.core.exceptions import WeatherQuotaExceededError
from weatherbot.domain.value_objects import UserHome, UserProfile, UserSubscription
from weatherbot.infrastructure.state import ConversationStateStore
from weatherbot.presentation.command_presenter import CommandPresenter, KeyboardView


class TranslatorSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def __call__(self, key: str, lang: str, **kwargs: object) -> str:
        self.calls.append((key, lang, kwargs))
        payload = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{key}:{lang}:{payload}" if payload else f"{key}:{lang}"


def _weather_formatter(
    report, *, place_label=None, lang
):  # pragma: no cover - simple stub
    return f"{place_label}:{lang}"


def _build_presenter(
    user_service: AsyncMock,
    weather_service: AsyncMock,
    translator: TranslatorSpy,
    state_store: ConversationStateStoreProtocol | None = None,
) -> CommandPresenter:
    return CommandPresenter(
        user_service,
        weather_service,
        translator,
        state_store or ConversationStateStore(),
        weather_formatter=_weather_formatter,
        help_context={
            "version": "1.0.0",
            "release_date": "2024-01-01",
            "languages": "ru,en",
        },
        reset_formatter=lambda reset_at, tz: f"{reset_at.isoformat()}@{tz}",
    )


def test_start_prompts_language_when_not_explicit():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    user_service.get_user_profile.return_value = UserProfile()
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.start(10))

    assert result.keyboard is KeyboardView.LANGUAGE
    assert result.message.startswith("Hello!")


def test_help_uses_metadata():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.help(42))

    assert (
        result.message
        == "help_message:en:languages=ru,en,release_date=2024-01-01,version=1.0.0"
    )
    assert translator.calls[0][2]["version"] == "1.0.0"


def test_set_home_prompt_sets_state():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    weather_service = AsyncMock()
    translator = TranslatorSpy()
    state_store = ConversationStateStore()

    presenter = _build_presenter(user_service, weather_service, translator, state_store)
    result = asyncio.run(presenter.set_home(5, None))

    assert result.success is True
    assert state_store.get_state(5).mode.name == "AWAITING_SETHOME"


def test_set_home_saves_coordinates():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    weather_service = AsyncMock()
    weather_service.geocode_city.return_value = GeocodeResultDTO(1.0, 2.0, "City")
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.set_home(8, " City "))

    user_service.set_user_home.assert_awaited_once_with("8", 1.0, 2.0, "City")
    assert result.message == "sethome_success:en:lat=1.0,location=City,lon=2.0"


def test_set_home_validation_error():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.set_home(9, "   "))

    assert result.success is False
    assert "cannot" in result.message.lower()


def test_home_weather_success_notifies_quota():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    user_service.get_user_home.return_value = UserHome(lat=1.0, lon=2.0, label="City")
    weather_service = AsyncMock()
    weather_service.get_weather_by_coordinates.return_value = SimpleNamespace()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.home_weather(77))

    assert result.notify_quota is True
    assert result.parse_mode == "HTML"
    assert result.message == "City:ru"


def test_home_weather_quota_exceeded():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    user_service.get_user_home.return_value = UserHome(
        lat=1.0, lon=2.0, label="City", timezone="Europe/Moscow"
    )
    weather_service = AsyncMock()
    weather_service.get_weather_by_coordinates.side_effect = WeatherQuotaExceededError(
        datetime(2024, 1, 1)
    )
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.home_weather(1))

    assert result.success is False
    assert "weather_quota_exceeded" in result.message
    assert result.notify_quota is True


def test_home_weather_without_home():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    user_service.get_user_home.return_value = None
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.home_weather(2))

    assert result.success is False
    assert result.message == "home_not_set:en"


def test_data_snapshot_renders_profile():
    profile = UserProfile(
        language="en",
        home=UserHome(lat=1.0, lon=2.0, label="Town", timezone="UTC"),
        subscription=UserSubscription(hour=9, minute=30),
        extras={"note": "extra"},
    )
    user_service = AsyncMock()
    user_service.get_user_profile.return_value = profile
    user_service.get_user_language.return_value = "en"
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.data_snapshot(12))

    assert "Town" in result.message
    assert "note: extra" in result.message


def test_delete_user_data_success():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    user_service.delete_user_data.return_value = True
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.delete_user_data(3))

    assert result.success is True
    assert result.message == "data_deleted:en"


def test_privacy_message():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "de"
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(presenter.privacy(4))

    assert result.message == "privacy_message:de"


def test_whoami_details():
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "en"
    weather_service = AsyncMock()
    translator = TranslatorSpy()

    presenter = _build_presenter(user_service, weather_service, translator)
    result = asyncio.run(
        presenter.whoami(
            5, user_id=5, first_name="John", last_name="Doe", username="jdoe"
        )
    )

    assert "jdoe" in result.message
    assert result.language == "en"
