import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.presentation.i18n import i18n

from ..infrastructure.spam_protection import spam_protection

logger = logging.getLogger(__name__)


def spam_check(handler):

    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):

        user_id = None
        if getattr(update, "effective_user", None):
            user_id = update.effective_user.id
        elif getattr(update, "callback_query", None) and getattr(
            update.callback_query, "from_user", None
        ):
            user_id = update.callback_query.from_user.id

        if user_id is None and getattr(update, "effective_chat", None):
            user_id = update.effective_chat.id
        if user_id is None:
            logger.warning("Failed to extract user_id from update")
            return

        message_text = ""
        if getattr(update, "message", None) and getattr(update.message, "text", None):
            message_text = update.message.text
        elif getattr(update, "callback_query", None) and getattr(
            update.callback_query, "data", None
        ):
            message_text = update.callback_query.data

        count_request = not (getattr(update, "callback_query", None) is not None)

        user_lang = "ru"
        try:
            from weatherbot.infrastructure.setup import get_user_service

            user_service = get_user_service()
            user_lang = await user_service.get_user_language(str(user_id)) or "ru"
        except Exception as e:
            logger.debug("Could not resolve user language for spam check (%s)", e)

        try:
            is_spam, reason = await spam_protection.is_spam(
                user_id, message_text, count_request=count_request, user_lang=user_lang
            )
        except Exception as e:
            logger.warning(f"Spam check failed, proceeding: {e}")
            is_spam, reason = False, None

        if is_spam:
            logger.warning(f"Spam from user {user_id}: {reason}")

            if reason != "SILENT_BLOCK":
                try:
                    if getattr(update, "message", None):
                        await update.message.reply_text(reason)
                    elif getattr(update, "callback_query", None):
                        await update.callback_query.answer(
                            f"⚠️ {reason}", show_alert=True
                        )
                except Exception as e:
                    logger.error(f"Failed to send spam warning message: {e}")

            return

        try:
            return await handler(update, context, *args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in handler {handler.__name__}: {e}")

            try:
                if getattr(update, "message", None):
                    await update.message.reply_text(
                        i18n.get("generic_error", user_lang)
                    )
                elif getattr(update, "callback_query", None):
                    await update.callback_query.answer(
                        i18n.get("generic_error_short", user_lang), show_alert=True
                    )
            except Exception as inner:
                logger.debug("Failed to send generic error message: %s", inner)

    return wrapper


def admin_only(admin_ids: set[int]):

    def decorator(handler):
        @wraps(handler)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user_id = update.effective_user.id if update.effective_user else None
            if user_id not in admin_ids:
                logger.warning(
                    f"Unauthorized attempt to access admin command by {user_id}"
                )
                user_lang = "ru"
                try:
                    from weatherbot.infrastructure.setup import get_user_service

                    user_service = get_user_service()
                    user_lang = await user_service.get_user_language(str(user_id))
                except Exception as e:
                    logger.debug(
                        "Could not resolve user language for admin-only notice: %s", e
                    )
                try:
                    if update.message:
                        await update.message.reply_text(
                            i18n.get("no_admin_rights", user_lang)
                        )
                    elif update.callback_query:
                        await update.callback_query.answer(
                            i18n.get("no_admin_rights", user_lang), show_alert=True
                        )
                except Exception as send_err:
                    logger.debug(
                        "Failed to send no_admin_rights message to %s: %s",
                        user_id,
                        send_err,
                    )
                return
            return await handler(update, context, *args, **kwargs)

        return wrapper

    return decorator
