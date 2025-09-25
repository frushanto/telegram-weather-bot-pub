from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.infrastructure.setup import get_user_service
from weatherbot.presentation.i18n import i18n
from weatherbot.presentation.keyboards import main_keyboard


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not update.callback_query:
        return

    data = update.callback_query.data or ""
    if not data.startswith("lang_"):
        await update.callback_query.answer()
        return

    lang = data.split("_", 1)[1]
    chat_id = update.effective_chat.id

    try:
        user_service = get_user_service()
        profile_before = await user_service.get_user_profile(str(chat_id))
        await user_service.set_user_language(str(chat_id), lang)

        lang_names = {"en": "English", "ru": "Русский", "de": "Deutsch"}
        language_name = lang_names.get(lang, lang)

        is_first_time = profile_before.is_empty()

        await update.callback_query.answer()

        if is_first_time:
            welcome_message = (
                f"✅ {i18n.get('language_changed', lang, language=language_name)}\n\n"
                f"{i18n.get('start_message', lang)}"
            )
            await update.callback_query.message.edit_text(
                welcome_message, reply_markup=None
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=i18n.get("keyboard_help_message", lang),
                reply_markup=main_keyboard(lang),
            )
        else:
            await update.callback_query.message.edit_text(
                i18n.get("language_changed", lang, language=language_name),
                reply_markup=None,
            )
    except Exception:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            i18n.get("language_change_error", "ru"),
            reply_markup=None,
        )
