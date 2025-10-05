"""Presenter helpers for command handlers.

This module coordinates the orchestration that previously lived directly inside
the Telegram command handlers.  Moving the logic here allows the handlers to
stay focused on transport concerns while the presenter performs application
coordination with strict typing and richer error mapping.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Iterable, Mapping, Optional

from weatherbot.application.dtos import GeocodeResultDTO
from weatherbot.application.interfaces import (
    ConversationStateStoreProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
)
from weatherbot.core.exceptions import (
    GeocodeServiceError,
    ValidationError,
    WeatherQuotaExceededError,
    WeatherServiceError,
)
from weatherbot.domain.conversation import ConversationMode
from weatherbot.domain.value_objects import UserHome, UserProfile
from weatherbot.presentation.validation import CityInputModel, validate_payload
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


class KeyboardView(Enum):
    """High level keyboard options understood by the handlers."""

    NONE = "none"
    MAIN = "main"
    LANGUAGE = "language"


@dataclass(frozen=True, slots=True)
class PresenterResponse:
    """Normalized payload returned from presenter interactions."""

    message: str
    language: str
    keyboard: KeyboardView = KeyboardView.MAIN
    parse_mode: Optional[str] = None
    success: bool = True
    notify_quota: bool = False


class CommandPresenter:
    """Coordinates user facing commands across services."""

    _LANGUAGE_PROMPT_TEXT = (
        "Hello! Привет! Hallo! 🌍\n\n"
        "I'm a weather bot that supports multiple languages.\n"
        "Я погодный бот с поддержкой нескольких языков.\n"
        "Ich bin ein Wetter-Bot mit Unterstützung für mehrere Sprachen.\n\n"
        "🌐 Please choose your language:\n"
        "🌐 Пожалуйста, выберите свой язык:\n"
        "🌐 Bitte wählen Sie Ihre Sprache:"
    )

    def __init__(
        self,
        user_service: UserServiceProtocol,
        weather_service: WeatherApplicationServiceProtocol,
        translator: Callable[..., str],
        state_store: ConversationStateStoreProtocol,
        *,
        weather_formatter: Callable[..., str],
        help_context: Optional[Mapping[str, object]] = None,
        reset_formatter: Callable[[datetime, Optional[str]], str] = format_reset_time,
    ) -> None:
        self._user_service = user_service
        self._weather_service = weather_service
        self._translate = translator
        self._state_store = state_store
        self._format_weather = weather_formatter
        self._format_reset_time = reset_formatter
        self._help_context = dict(help_context or {})

    async def start(self, chat_id: int) -> PresenterResponse:
        """Return greeting or language prompt message for the user."""

        language = await self._user_service.get_user_language(str(chat_id))
        profile = await self._user_service.get_user_profile(str(chat_id))

        if not profile.language_explicit:
            return PresenterResponse(
                message=self._LANGUAGE_PROMPT_TEXT,
                language=language,
                keyboard=KeyboardView.LANGUAGE,
            )

        text = self._translate("start_message", language)
        return PresenterResponse(message=text, language=language)

    async def help(self, chat_id: int) -> PresenterResponse:
        """Prepare help message with runtime metadata."""

        language = await self._user_service.get_user_language(str(chat_id))
        text = self._translate("help_message", language, **self._help_context)
        return PresenterResponse(message=text, language=language)

    async def set_home(
        self, chat_id: int, city_input: Optional[str]
    ) -> PresenterResponse:
        """Handle `/sethome` flow for the provided input."""

        language = await self._user_service.get_user_language(str(chat_id))

        if not city_input:
            self._state_store.set_awaiting_mode(
                chat_id, ConversationMode.AWAITING_SETHOME
            )
            message = self._translate("sethome_prompt", language)
            return PresenterResponse(message=message, language=language)

        try:
            payload = validate_payload(CityInputModel, city=city_input)
        except ValidationError as err:
            logger.warning("Invalid city input for chat %s: %s", chat_id, err)
            return PresenterResponse(
                message=str(err),
                language=language,
                success=False,
            )

        city = payload.city
        try:
            geocode_result = await self._weather_service.geocode_city(city)
        except GeocodeServiceError as err:
            logger.warning("Geocode error for chat %s: %s", chat_id, err)
            message = self._translate("sethome_failed", language, city=city)
            return PresenterResponse(message=message, language=language, success=False)

        if not geocode_result:
            message = self._translate("sethome_failed", language, city=city)
            return PresenterResponse(message=message, language=language, success=False)

        lat, lon, label = self._unpack_geocode_result(geocode_result)
        await self._user_service.set_user_home(str(chat_id), lat, lon, label)

        message = self._translate(
            "sethome_success", language, location=label, lat=lat, lon=lon
        )
        return PresenterResponse(message=message, language=language)

    async def home_weather(self, chat_id: int) -> PresenterResponse:
        """Return formatted weather for the user's saved home."""

        language = await self._user_service.get_user_language(str(chat_id))
        home = await self._user_service.get_user_home(str(chat_id))

        if home is None:
            message = self._translate("home_not_set", language)
            return PresenterResponse(message=message, language=language, success=False)

        try:
            weather = await self._weather_service.get_weather_by_coordinates(
                home.lat, home.lon
            )
            message = self._format_weather(
                weather, place_label=home.label, lang=language
            )
            return PresenterResponse(
                message=message,
                language=language,
                parse_mode="HTML",
                notify_quota=True,
            )
        except WeatherQuotaExceededError as err:
            reset_text = self._format_reset_time(err.reset_at, home.timezone)
            message = self._translate(
                "weather_quota_exceeded", language, reset_time=reset_text
            )
            return PresenterResponse(
                message=message,
                language=language,
                success=False,
                notify_quota=True,
            )
        except WeatherServiceError as err:
            logger.warning("Weather service error for chat %s: %s", chat_id, err)
            message = self._translate("weather_error", language)
            return PresenterResponse(message=message, language=language, success=False)

    async def unset_home(self, chat_id: int) -> PresenterResponse:
        """Remove user's home if present."""

        language = await self._user_service.get_user_language(str(chat_id))
        removed = await self._user_service.remove_user_home(str(chat_id))
        key = "home_removed" if removed else "home_not_set"
        message = self._translate(key, language)
        return PresenterResponse(message=message, language=language, success=removed)

    async def data_snapshot(self, chat_id: int) -> PresenterResponse:
        """Render user data summary."""

        profile = await self._user_service.get_user_profile(str(chat_id))
        default_lang = await self._user_service.get_user_language(str(chat_id))
        language = profile.language or default_lang

        if profile.is_empty():
            message = self._translate("no_data_stored", language)
            return PresenterResponse(message=message, language=language, success=False)

        lines: list[str] = [f"💾 {self._translate('your_data', language)}:"]
        if profile.home:
            self._append_home_details(lines, profile.home, language)
        if profile.subscription:
            self._append_subscription_details(
                lines, profile, profile.subscription, language
            )
        if profile.language:
            lines.append(
                f"🌐 {self._translate('language', language)}: {profile.language}"
            )
        for key, value in profile.extras.items():
            lines.append(f"• {key}: {value}")

        message = "\n".join(lines)
        return PresenterResponse(message=message, language=language)

    async def delete_user_data(self, chat_id: int) -> PresenterResponse:
        """Delete user data snapshot and report outcome."""

        language = await self._user_service.get_user_language(str(chat_id))
        deleted = await self._user_service.delete_user_data(str(chat_id))
        key = "data_deleted" if deleted else "no_data_to_delete"
        message = self._translate(key, language)
        return PresenterResponse(message=message, language=language, success=deleted)

    async def privacy(self, chat_id: int) -> PresenterResponse:
        """Return privacy policy text."""

        language = await self._user_service.get_user_language(str(chat_id))
        message = self._translate("privacy_message", language)
        return PresenterResponse(message=message, language=language)

    async def whoami(
        self,
        chat_id: int,
        *,
        user_id: int,
        first_name: Optional[str],
        last_name: Optional[str],
        username: Optional[str],
    ) -> PresenterResponse:
        """Return diagnostic information about the Telegram user."""

        language = await self._user_service.get_user_language(str(chat_id))
        details: list[str] = [f"🆔 ID: {user_id}"]

        if first_name:
            details.append(
                f"👤 {self._translate('first_name', language)}: {first_name}"
            )
        if last_name:
            details.append(f"👤 {self._translate('last_name', language)}: {last_name}")
        if username:
            details.append(f"📝 {self._translate('username', language)}: @{username}")

        details.append(f"💬 {self._translate('chat_id', language)}: {chat_id}")
        details.append(f"🌐 {self._translate('language', language)}: {language}")

        return PresenterResponse(
            message="\n".join(details), language=language, success=True
        )

    def _append_home_details(
        self, lines: list[str], home: UserHome, language: str
    ) -> None:
        label = home.label or self._translate("unknown_location", language)
        lines.append(f"🏠 {self._translate('home_address', language)}: {label}")
        lines.append(
            "📍 "
            f"{self._translate('coordinates', language)}: {home.lat:.4f}, {home.lon:.4f}"
        )
        if home.timezone:
            lines.append(f"🕒 {self._translate('timezone', language)}: {home.timezone}")

    def _append_subscription_details(
        self,
        lines: list[str],
        profile: UserProfile,
        subscription: object,
        language: str,
    ) -> None:
        timezone_info = ""
        if profile.home and profile.home.timezone:
            timezone_info = f" ({profile.home.timezone})"
        lines.append(
            "🔔 "
            f"{self._translate('subscription', language)}: "
            f"{subscription.hour:02d}:{subscription.minute:02d}{timezone_info}"
        )

    @staticmethod
    def _unpack_geocode_result(result: object) -> tuple[float, float, str]:
        """Support legacy tuples as well as DTO objects."""

        if isinstance(result, GeocodeResultDTO):
            return result.lat, result.lon, result.label

        if isinstance(result, Mapping):
            lat = float(result["lat"])  # type: ignore[index]
            lon = float(result["lon"])  # type: ignore[index]
            label = str(result["label"])  # type: ignore[index]
            return lat, lon, label

        if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
            items = list(result)
            if len(items) >= 3:
                lat, lon, label = items[:3]
                return float(lat), float(lon), str(label)

        lat, lon, label = result  # type: ignore[misc]
        return float(lat), float(lon), str(label)


__all__ = [
    "CommandPresenter",
    "KeyboardView",
    "PresenterResponse",
]
