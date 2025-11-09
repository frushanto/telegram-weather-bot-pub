"""
Test text normalization utilities for button matching.

Covers emoji handling, unicode variations, case insensitivity, and whitespace normalization.
"""

import pytest

from weatherbot.utils.text import matches_button, normalize_button_text


class TestNormalizeButtonText:
    """Test normalize_button_text function with various inputs."""

    def test_removes_info_emoji(self):
        """Info emoji (ℹ️) should be removed."""
        assert normalize_button_text("ℹ️ Hilfe") == "hilfe"
        assert normalize_button_text("ℹ️ Help") == "help"
        assert normalize_button_text("ℹ️ Помощь") == "помощь"

    def test_removes_weather_emojis(self):
        """Weather-related emojis should be removed."""
        assert normalize_button_text("☁️ Stadtwetter") == "stadtwetter"
        assert normalize_button_text("🏠 Heimatwetter") == "heimatwetter"

    def test_removes_other_emojis(self):
        """Other button emojis should be removed."""
        assert normalize_button_text("➕ Zuhause festlegen") == "zuhause festlegen"
        assert normalize_button_text("🗑 Zuhause entfernen") == "zuhause entfernen"

    def test_lowercases_text(self):
        """Text should be converted to lowercase."""
        assert normalize_button_text("HILFE") == "hilfe"
        assert normalize_button_text("Help") == "help"
        assert normalize_button_text("HelP") == "help"

    def test_strips_whitespace(self):
        """Leading and trailing whitespace should be removed."""
        assert normalize_button_text("  Hilfe  ") == "hilfe"
        assert normalize_button_text("\tHelp\n") == "help"

    def test_collapses_internal_whitespace(self):
        """Multiple internal spaces should collapse to one."""
        assert normalize_button_text("Home  Weather") == "home weather"
        assert normalize_button_text("Set   Home") == "set home"

    def test_handles_empty_string(self):
        """Empty string should remain empty after normalization."""
        assert normalize_button_text("") == ""

    def test_handles_emoji_only(self):
        """String with only emoji should become empty."""
        assert normalize_button_text("ℹ️") == ""
        assert normalize_button_text("☁️🏠") == ""

    def test_unicode_normalization(self):
        """Unicode should be normalized to NFC form."""
        # Combined vs decomposed forms should normalize to same result
        combined = "ℹ️"  # U+2139 + variation selector
        text_with_combined = f"{combined} Hilfe"
        assert "hilfe" in normalize_button_text(text_with_combined)

    def test_preserves_cyrillic(self):
        """Cyrillic characters should be preserved (lowercased)."""
        assert normalize_button_text("Помощь") == "помощь"
        assert normalize_button_text("ПОМОЩЬ") == "помощь"

    def test_preserves_german_characters(self):
        """German special characters should be preserved (lowercased)."""
        assert normalize_button_text("Müller") == "müller"
        assert normalize_button_text("ÜBER") == "über"


class TestMatchesButton:
    """Test matches_button function for reliable button text comparison."""

    def test_exact_match_with_emoji(self):
        """Exact matches including emoji should return True."""
        assert matches_button("ℹ️ Hilfe", "ℹ️ Hilfe") is True
        assert matches_button("ℹ️ Help", "ℹ️ Help") is True

    def test_match_without_emoji_in_user_input(self):
        """User input without emoji should match label with emoji."""
        assert matches_button("Hilfe", "ℹ️ Hilfe") is True
        assert matches_button("Help", "ℹ️ Help") is True
        assert matches_button("Помощь", "ℹ️ Помощь") is True

    def test_match_case_insensitive(self):
        """Matching should be case-insensitive."""
        assert matches_button("HILFE", "ℹ️ Hilfe") is True
        assert matches_button("hilfe", "ℹ️ Hilfe") is True
        assert matches_button("HeLp", "ℹ️ Help") is True

    def test_match_with_extra_whitespace(self):
        """Extra whitespace should not prevent matching."""
        assert matches_button("  Hilfe  ", "ℹ️ Hilfe") is True
        assert matches_button("Help ", "ℹ️ Help") is True

    def test_no_match_different_words(self):
        """Different words should not match."""
        assert matches_button("Wetter", "ℹ️ Hilfe") is False
        assert matches_button("Home", "ℹ️ Help") is False

    def test_match_multi_word_buttons(self):
        """Multi-word button labels should match."""
        assert matches_button("Stadtwetter", "☁️ Stadtwetter") is True
        assert matches_button("City Weather", "☁️ City Weather") is True

    def test_no_match_partial_text(self):
        """Partial text should not match."""
        assert matches_button("Hilf", "ℹ️ Hilfe") is False
        assert matches_button("Hel", "ℹ️ Help") is False

    def test_cyrillic_button_matching(self):
        """Cyrillic buttons should match correctly."""
        assert matches_button("Помощь", "ℹ️ Помощь") is True
        assert matches_button("ПОМОЩЬ", "ℹ️ Помощь") is True
        assert matches_button("помощь", "ℹ️ Помощь") is True

    def test_weather_buttons_match(self):
        """All weather-related buttons should match correctly."""
        assert matches_button("Stadtwetter", "☁️ Stadtwetter") is True
        assert matches_button("Heimatwetter", "🏠 Heimatwetter") is True
        assert matches_button("Zuhause festlegen", "➕ Zuhause festlegen") is True
        assert matches_button("Zuhause entfernen", "🗑 Zuhause entfernen") is True


class TestButtonMatchingRegression:
    """Regression tests for reported bug scenarios."""

    def test_german_help_button_without_emoji(self):
        """
        Regression test: German Help button pressed without emoji.

        Bug: User presses "Hilfe" button, Telegram sends "Hilfe" (no emoji),
        but handler expects "ℹ️ Hilfe", causing weather lookup instead of help.
        """
        assert matches_button("Hilfe", "ℹ️ Hilfe") is True

    def test_russian_help_button_variations(self):
        """Russian Help button should match with/without emoji."""
        assert matches_button("Помощь", "ℹ️ Помощь") is True
        assert matches_button("помощь", "ℹ️ Помощь") is True
        assert matches_button("ПОМОЩЬ", "ℹ️ Помощь") is True

    def test_english_help_button_variations(self):
        """English Help button should match with/without emoji."""
        assert matches_button("Help", "ℹ️ Help") is True
        assert matches_button("help", "ℹ️ Help") is True
        assert matches_button("HELP", "ℹ️ Help") is True

    def test_language_button_constant(self):
        """Language button (no emoji in constant) should match."""
        # BTN_LANGUAGE = "🌐 Language" but might come as "Language"
        assert matches_button("Language", "🌐 Language") is True
        assert matches_button("language", "🌐 Language") is True
