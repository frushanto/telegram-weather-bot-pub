from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from .i18n import i18n

BTN_LANGUAGE = "🌐 Language"


def main_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    rows = [
        [
            i18n.get("weather_city_button", language),
            i18n.get("weather_home_button", language),
        ],
        [
            i18n.get("set_home_button", language),
            i18n.get("remove_home_button", language),
        ],
        [i18n.get("help_button", language), BTN_LANGUAGE],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def language_keyboard() -> InlineKeyboardMarkup:

    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
