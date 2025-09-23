import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.presentation.i18n import i18n


class TestMultiLanguageSupport:

    @pytest.fixture
    def languages(self):

        return ["ru", "en", "de"]

    @pytest.fixture
    def load_locales(self, languages):

        locales = {}
        import os

        base_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        for lang in languages:
            try:
                path = os.path.join(base_dir, f"{lang}.json")
                with open(path, "r", encoding="utf-8") as f:
                    locales[lang] = json.load(f)
            except FileNotFoundError:
                locales[lang] = {}
        return locales

    def test_all_languages_have_required_keys(self, load_locales, languages):

        required_keys = {
            "start_message",
            "help_message",
            "weather_prompt",
            "no_arguments",
            "sethome_success",
            "sethome_failed",
            "home_not_set",
            "home_removed",
            "subscribe_success",
            "unsubscribe_success",
            "privacy_message",
            "data_message",
        }

        ru_keys = set(load_locales.get("ru", {}).keys())
        for lang in languages:
            locale_keys = set(load_locales.get(lang, {}).keys())

            missing_keys = required_keys - locale_keys
            assert not missing_keys, f"В языке {lang} отсутствуют ключи: {missing_keys}"

    def test_i18n_get_all_languages(self, languages):

        test_key = "start_message"
        for lang in languages:
            result = i18n.get(test_key, lang)
            assert (
                result is not None
            ), f"Не получена строка для {test_key} на языке {lang}"
            assert isinstance(result, str), f"Результат для {lang} не является строкой"
            assert len(result) > 0, f"Пустая строка для {test_key} на языке {lang}"

    def test_i18n_get_with_fallback(self):

        non_existent_key = "non_existent_key_12345"
        default_value = "Default message"
        result = i18n.get(non_existent_key, "en", default=default_value)
        assert result == default_value

    def test_i18n_formatting_with_parameters(self):

        result = i18n.get(
            "sethome_success", "ru", location="Москва", lat=55.75, lon=37.61
        )
        assert "Москва" in result

        result = i18n.get(
            "sethome_success", "en", location="London", lat=51.5, lon=-0.1
        )
        assert "London" in result

    def test_keyboard_buttons_all_languages(self, languages):

        from weatherbot.presentation.keyboards import main_keyboard

        for lang in languages:
            keyboard = main_keyboard(lang)
            assert keyboard is not None, f"Клавиатура не создана для языка {lang}"

            buttons = keyboard.keyboard
            assert len(buttons) > 0, f"Нет кнопок для языка {lang}"

            for row in buttons:
                for button in row:
                    assert len(button.text) > 0, f"Пустая кнопка для языка {lang}"

    def test_weather_formatting_all_languages(self, languages):

        from weatherbot.presentation.formatter import format_weather

        mock_weather_data = {
            "temperature": 15,
            "feels_like": 12,
            "description": "clear sky",
            "place": "Test City",
            "wind_speed": 5.2,
            "humidity": 65,
            "pressure": 1013,
        }
        for lang in languages:
            with patch("weatherbot.presentation.i18n.i18n.get") as mock_i18n:

                mock_i18n.side_effect = (
                    lambda key, language=None, **kwargs: f"{key}_{language}"
                )
                result = format_weather(mock_weather_data)
                assert (
                    result is not None
                ), f"Форматирование погоды провалилось для {lang}"
                assert len(result) > 0, f"Пустое форматирование погоды для {lang}"

    @pytest.mark.asyncio
    async def test_command_responses_all_languages(self, languages):

        from weatherbot.handlers.commands import start_cmd

        for lang in languages:
            update = MagicMock()
            update.effective_chat.id = 123456
            update.message.reply_text = AsyncMock()
            context = MagicMock()
            with (
                patch("weatherbot.handlers.commands.get_user_service") as mock_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
            ):
                user_service = AsyncMock()
                user_service.get_user_language = AsyncMock(return_value=lang)
                mock_service.return_value = user_service
                mock_i18n.return_value = f"Start message for {lang}"
                await start_cmd(update, context)

                user_service.get_user_language.assert_called_once_with("123456")
                assert update.message.reply_text.call_count >= 1

                update.message.reply_text.assert_called()

    def test_language_consistency(self, load_locales, languages):

        for lang, locale in load_locales.items():
            for key, value in locale.items():

                assert value.strip(), f"Пустое значение для ключа {key} в языке {lang}"

                if "{" in value and "}" in value:

                    pass

                if lang != "ru" and "ru" in load_locales:
                    assert (
                        key in load_locales["ru"]
                    ), f"Ключ {key} есть в {lang}, но нет в ru"

    def test_error_messages_all_languages(self, languages):

        error_keys = [
            "weather_error",
            "sethome_failed",
            "home_not_set",
            "subscribe_invalid_time",
            "unsubscribe_not_found",
        ]
        for lang in languages:
            for key in error_keys:
                result = i18n.get(key, lang, default=f"Error message {key}")
                assert result is not None
                assert len(result) > 0

                assert any(
                    indicator in result.lower()
                    for indicator in ["❌", "error", "ошибка", "fehler"]
                )

    def test_help_messages_completeness(self, load_locales, languages):

        for lang in languages:
            locale = load_locales.get(lang, {})

            if "help_message" in locale:
                help_msg = locale["help_message"]

                commands = ["/weather", "/sethome", "/subscribe", "/help"]
                for cmd in commands:

                    pass

            if "start_message" in locale:
                start_msg = locale["start_message"]
                assert (
                    len(start_msg) > 50
                ), f"Стартовое сообщение слишком короткое для {lang}"
