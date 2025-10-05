from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.application.interfaces import UserServiceProtocol
from weatherbot.presentation.i18n import Localization

KeyboardFactory = Callable[[str], object]


@dataclass(slots=True)
class LanguageHandlerDependencies:
    user_service: UserServiceProtocol
    localization: Localization
    keyboard_factory: KeyboardFactory


_deps: LanguageHandlerDependencies | None = None


def configure_language_handlers(deps: LanguageHandlerDependencies) -> None:
    global _deps
    _deps = deps


def _require_deps() -> LanguageHandlerDependencies:
    if _deps is None:
        raise RuntimeError("Language handler dependencies are not configured")
    return _deps


def get_user_service() -> UserServiceProtocol:
    return _require_deps().user_service


def _get_localization() -> Localization:
    return _require_deps().localization


def _get_keyboard(lang: str) -> object:
    return _require_deps().keyboard_factory(lang)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not update.callback_query:
        return

    data = update.callback_query.data or ""
    if not data.startswith("lang_"):
        await update.callback_query.answer()
        return

    lang = data.split("_", 1)[1]
    chat_id = update.effective_chat.id

    user_service = get_user_service()
    localization = _get_localization()

    try:
        profile_before = await user_service.get_user_profile(str(chat_id))
        await user_service.set_user_language(str(chat_id), lang)

        lang_names = {"en": "English", "ru": "Русский", "de": "Deutsch"}
        language_name = lang_names.get(lang, lang)

        is_first_time = profile_before.is_empty()

        await update.callback_query.answer()

        if is_first_time:
            welcome_message = (
                f"✅ {localization.get('language_changed', lang, language=language_name)}\n\n"
                f"{localization.get('start_message', lang)}"
            )
            await update.callback_query.message.edit_text(
                welcome_message, reply_markup=None
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=localization.get("keyboard_help_message", lang),
                reply_markup=_get_keyboard(lang),
            )
        else:
            await update.callback_query.message.edit_text(
                localization.get("language_changed", lang, language=language_name),
                reply_markup=None,
            )
    except Exception:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            localization.get("language_change_error", "ru"),
            reply_markup=None,
        )
