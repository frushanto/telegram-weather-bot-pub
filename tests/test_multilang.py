from unittest.mock import MagicMock, patch

import pytest

from weatherbot.presentation.i18n import i18n
from weatherbot.presentation.keyboards import language_keyboard, main_keyboard


class TestBasicMultilang:

    def test_i18n_basic_functionality(self):

        result_ru = i18n.get("start_message", "ru")
        assert result_ru is not None
        assert len(result_ru) > 0

        result_en = i18n.get("start_message", "en")
        assert result_en is not None
        assert len(result_en) > 0

        assert result_ru != result_en

    def test_language_fallback(self):

        expected_ru = i18n.get("start_message", "ru")
        result = i18n.get("start_message", "unknown_lang", default="Fallback message")
        assert result == expected_ru

    def test_keyboard_localization(self):

        kb_ru = main_keyboard("ru")
        kb_en = main_keyboard("en")
        assert kb_ru is not None
        assert kb_en is not None

        assert len(kb_ru.keyboard) > 0
        assert len(kb_en.keyboard) > 0

    def test_language_keyboard_structure(self):

        kb = language_keyboard()
        assert kb is not None
        assert hasattr(kb, "inline_keyboard")
        assert len(kb.inline_keyboard) > 0

        buttons_data = []
        for row in kb.inline_keyboard:
            for button in row:
                buttons_data.append(button.callback_data)
        assert "lang_ru" in buttons_data
        assert "lang_en" in buttons_data
        assert "lang_de" in buttons_data
