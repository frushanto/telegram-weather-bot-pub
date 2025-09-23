"""
Tests for newly added i18n keys during the Russian text cleanup.
Tests language selection keys, error messages, and consistency.
"""

import pytest

from weatherbot.presentation.i18n import i18n


class TestNewI18nKeys:
    """Test suite for new i18n keys added during Russian text cleanup."""

    @pytest.fixture
    def languages(self):
        """Supported languages."""
        return ["ru", "en", "de"]

    def test_language_selection_keys_exist(self, languages):
        """Test that all language selection keys exist in all languages."""
        required_keys = [
            "language_selection_header",
            "language_selection_instructions",
            "language_not_recognized",
        ]

        for lang in languages:
            for key in required_keys:
                value = i18n.get(key, lang)
                assert value, f"Key '{key}' is empty for language '{lang}'"
                assert (
                    key not in value
                ), f"Key '{key}' returned key name instead of translation for language '{lang}'"

    def test_language_selection_header_content(self, languages):
        """Test that language selection header contains expected content."""
        for lang in languages:
            header = i18n.get("language_selection_header", lang)

            # Should contain the language icon
            assert "🌐" in header, f"Language header missing emoji for {lang}"

            # Should contain multilingual text
            assert (
                "Choose language" in header
            ), f"Missing English text in header for {lang}"
            assert (
                "Sprache wählen" in header
            ), f"Missing German text in header for {lang}"

    def test_language_not_recognized_multilingual(self, languages):
        """Test that language not recognized message is multilingual."""
        for lang in languages:
            message = i18n.get("language_not_recognized", lang)

            # Should contain error indicator
            assert "❌" in message, f"Missing error emoji for {lang}"

            # Should contain text in multiple languages for user guidance
            assert (
                "Language not recognized" in message or "Язык не распознан" in message
            ), f"Missing recognition error text for {lang}"

    def test_generic_error_consistency(self, languages):
        """Test that generic error messages are consistent and appropriate."""
        for lang in languages:
            error_msg = i18n.get("generic_error", lang)

            assert error_msg, f"Generic error message empty for {lang}"
            assert len(error_msg) > 10, f"Generic error message too short for {lang}"

            # Should indicate an error occurred
            if lang == "ru":
                assert "ошибка" in error_msg.lower(), "Missing 'error' word in Russian"
            elif lang == "en":
                assert "error" in error_msg.lower(), "Missing 'error' word in English"
            elif lang == "de":
                assert "fehler" in error_msg.lower(), "Missing 'error' word in German"

    def test_language_selection_instructions_completeness(self, languages):
        """Test that language selection instructions cover all supported languages."""
        for lang in languages:
            instructions = i18n.get("language_selection_instructions", lang)

            # Should contain instructions for Russian
            assert (
                "русский" in instructions or "ru" in instructions
            ), f"Missing Russian instructions for {lang}"

            # Should contain instructions for English
            assert (
                "english" in instructions or "en" in instructions
            ), f"Missing English instructions for {lang}"

            # Should contain instructions for German
            assert (
                "deutsch" in instructions or "de" in instructions
            ), f"Missing German instructions for {lang}"

            # Should contain cancel instruction
            assert "/cancel" in instructions, f"Missing cancel instruction for {lang}"

    def test_new_keys_no_hardcoded_defaults(self, languages):
        """Test that new keys don't contain hardcoded defaults or key names."""
        new_keys = [
            "language_selection_header",
            "language_selection_instructions",
            "language_not_recognized",
            "generic_error",
        ]

        for lang in languages:
            for key in new_keys:
                value = i18n.get(key, lang)

                # Should not return the key name itself
                assert (
                    value != key
                ), f"Key '{key}' returns key name for language '{lang}'"

                # Should not contain placeholder text
                assert (
                    "TODO" not in value.upper()
                ), f"Key '{key}' contains TODO for language '{lang}'"
                assert (
                    "PLACEHOLDER" not in value.upper()
                ), f"Key '{key}' contains placeholder for language '{lang}'"

    def test_russian_fallback_behavior(self):
        """Test that Russian fallback works correctly for new keys."""
        new_keys = [
            "language_selection_header",
            "language_selection_instructions",
            "language_not_recognized",
            "generic_error",
        ]

        for key in new_keys:
            # Test with invalid language - should fallback to Russian
            ru_value = i18n.get(key, "ru")
            fallback_value = i18n.get(key, "invalid_lang")

            assert (
                ru_value == fallback_value
            ), f"Russian fallback not working for key '{key}'"

    def test_parameter_support_in_new_keys(self):
        """Test that new keys handle parameters correctly if they support them."""
        # Test keys that might use parameters
        test_cases = [
            ("generic_error", {"user": "test"}),
            ("language_not_recognized", {"input": "test"}),
        ]

        for key, params in test_cases:
            for lang in ["ru", "en", "de"]:
                # Should not crash with extra parameters
                try:
                    result = i18n.get(key, lang, **params)
                    assert (
                        result
                    ), f"Key '{key}' returned empty with parameters for {lang}"
                except Exception as e:
                    pytest.fail(f"Key '{key}' failed with parameters for {lang}: {e}")

    def test_language_selection_flow_completeness(self, languages):
        """Test that language selection flow has all necessary components."""
        # Test the complete flow
        for lang in languages:
            # 1. Header should invite language selection
            header = i18n.get("language_selection_header", lang)
            assert header, f"Missing language selection header for {lang}"

            # 2. Instructions should explain how to select
            instructions = i18n.get("language_selection_instructions", lang)
            assert instructions, f"Missing language selection instructions for {lang}"

            # 3. Error message for invalid input
            error = i18n.get("language_not_recognized", lang)
            assert error, f"Missing language not recognized message for {lang}"

            # 4. Success message when language is changed
            success = i18n.get("language_changed", lang)
            assert success, f"Missing language changed message for {lang}"

    def test_consistency_with_existing_error_keys(self, languages):
        """Test that new error keys are consistent with existing ones."""
        error_keys = ["generic_error", "weather_error", "language_change_error"]

        for lang in languages:
            for key in error_keys:
                value = i18n.get(key, lang)

                # Should indicate an error
                if lang == "ru":
                    assert (
                        "❌" in value or "ошибка" in value.lower()
                    ), f"Error key '{key}' doesn't indicate error in Russian"
                elif lang == "en":
                    assert (
                        "❌" in value or "error" in value.lower()
                    ), f"Error key '{key}' doesn't indicate error in English"
                elif lang == "de":
                    assert (
                        "❌" in value or "fehler" in value.lower()
                    ), f"Error key '{key}' doesn't indicate error in German"
