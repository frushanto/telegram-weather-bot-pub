from unittest.mock import AsyncMock, MagicMock

import pytest

from weatherbot.presentation.i18n import Localization
from weatherbot.presentation.keyboards import (
    BTN_LANGUAGE,
    language_keyboard,
    main_keyboard,
)


class TestKeyboards:

    def test_main_keyboard_default(self):

        keyboard = main_keyboard()
        assert keyboard is not None
        assert hasattr(keyboard, "keyboard")
        assert len(keyboard.keyboard) > 0

    def test_language_keyboard(self):

        keyboard = language_keyboard()
        assert keyboard is not None

        assert hasattr(keyboard, "inline_keyboard")

        keyboard_text = str(keyboard.inline_keyboard)
        assert "ru" in keyboard_text or "en" in keyboard_text or "de" in keyboard_text

    def test_main_keyboard_different_languages(self):

        languages = ["ru", "en", "de"]
        for lang in languages:
            keyboard = main_keyboard(lang)
            assert keyboard is not None
            assert len(keyboard.keyboard) > 0

            buttons_found = 0
            for row in keyboard.keyboard:
                for button in row:
                    if hasattr(button, "text"):
                        buttons_found += 1
                    elif isinstance(button, str):
                        buttons_found += 1
            assert buttons_found > 0


class TestKeyboardButtons:

    def test_keyboard_has_structure(self):

        keyboard = main_keyboard()

        assert hasattr(keyboard, "keyboard")
        assert isinstance(keyboard.keyboard, (list, tuple))

        for row in keyboard.keyboard:
            assert isinstance(row, (list, tuple))
            assert len(row) > 0

    def test_language_keyboard_structure(self):

        keyboard = language_keyboard()

        assert hasattr(keyboard, "inline_keyboard")
        assert isinstance(keyboard.inline_keyboard, (list, tuple))
        assert len(keyboard.inline_keyboard) > 0

        found_buttons = False
        for row in keyboard.inline_keyboard:
            if len(row) > 0:
                found_buttons = True
                break
        assert found_buttons


class TestInlineMenus:

    def test_language_keyboard_buttons(self):

        keyboard = language_keyboard()
        keyboard_text = str(keyboard.inline_keyboard)

        assert "lang_ru" in keyboard_text
        assert "lang_en" in keyboard_text
        assert "lang_de" in keyboard_text

        assert "🇷🇺" in keyboard_text
        assert "🇺🇸" in keyboard_text
        assert "🇩🇪" in keyboard_text


class TestKeyboardInteractions:

    @pytest.mark.asyncio
    async def test_language_keyboard_callback(self):
        import weatherbot.handlers.language as language_module

        update = MagicMock()
        update.callback_query.data = "lang_en"
        update.callback_query.answer = AsyncMock()
        update.callback_query.message.edit_text = AsyncMock()
        update.effective_chat.id = 123456
        context = MagicMock()
        context.bot = AsyncMock()

        user_service = AsyncMock()
        user_service.set_user_language = AsyncMock()

        language_module.configure_language_handlers(
            language_module.LanguageHandlerDependencies(
                user_service=user_service,
                localization=Localization(),
                keyboard_factory=lambda _lang: None,
            )
        )

        await language_module.language_callback(update, context)

        user_service.set_user_language.assert_awaited_once_with("123456", "en")

    def test_keyboard_button_consistency(self):

        buttons = [
            BTN_LANGUAGE,
        ]
        for button in buttons:
            assert isinstance(button, str)
            assert len(button) > 0

    def test_keyboard_special_characters(self):

        keyboard = main_keyboard()

        keyboard_str = str(keyboard)

        assert len(keyboard_str) > 10
