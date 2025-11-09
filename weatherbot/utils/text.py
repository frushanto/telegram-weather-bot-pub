"""Text normalization utilities for reliable button and command matching."""

import re
import unicodedata


def normalize_button_text(text: str) -> str:
    """
    Normalize button text for reliable matching.

    Handles:
    - Unicode normalization (NFC form)
    - Emoji removal (info symbol, flags, weather icons, etc.)
    - Whitespace normalization (strip, collapse multiple spaces)
    - Case normalization (lowercase)

    Args:
        text: Raw button text from Telegram

    Returns:
        Normalized text suitable for comparison

    Examples:
        >>> normalize_button_text("ℹ️ Hilfe  ")
        'hilfe'
        >>> normalize_button_text("  HELP ")
        'help'
        >>> normalize_button_text("🏠 Home Weather")
        'home weather'
    """
    # Normalize unicode to NFC form (canonical composition)
    text = unicodedata.normalize("NFC", text)

    # Remove common emoji patterns:
    # - Info symbol (ℹ️ U+2139 + variation selector)
    # - Weather/home icons (☁️🏠➕🗑)
    # - Flag emojis and other symbols
    # Use comprehensive emoji regex pattern
    emoji_pattern = re.compile(
        "["
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "\U000024c2-\U0001f251"
        "\u2139\ufe0f"  # Info symbol with variation selector
        "\u2139"  # Info symbol without variation selector
        "\u2601"  # Cloud
        "\u2600"  # Sun
        "\u26c5"  # Sun behind cloud
        "\ufe0f"  # Variation selector-16 (makes preceding char emoji-style)
        "]+"
    )
    text = emoji_pattern.sub("", text)

    # Normalize whitespace: strip leading/trailing, collapse internal
    text = " ".join(text.split())

    # Convert to lowercase for case-insensitive comparison
    text = text.lower()

    return text


def matches_button(user_text: str, expected_label: str) -> bool:
    """
    Check if user-provided text matches expected button label.

    Performs normalization on both sides before comparison to handle:
    - Emoji variations (present/absent, different unicode representations)
    - Case differences
    - Whitespace variations

    Args:
        user_text: Text received from Telegram (button press or typed message)
        expected_label: Expected button label from i18n (e.g., "ℹ️ Hilfe")

    Returns:
        True if texts match after normalization, False otherwise

    Examples:
        >>> matches_button("Hilfe", "ℹ️ Hilfe")
        True
        >>> matches_button("ℹ️ HILFE", "ℹ️ Hilfe")
        True
        >>> matches_button("help", "ℹ️ Help")
        True
    """
    return normalize_button_text(user_text) == normalize_button_text(expected_label)
