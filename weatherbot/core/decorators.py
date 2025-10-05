import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.core.container import get_container

logger = logging.getLogger(__name__)

SpamServiceProvider = Callable[[], Any]
UserLanguageResolver = Callable[[int], Awaitable[str]]
Translator = Callable[..., str]


def _identity_translator(key: str, *_args: Any, **_kwargs: Any) -> str:

    return key


@dataclass
class DecoratorDependencies:

    spam_service: Any | None = None
    spam_service_provider: SpamServiceProvider | None = None
    user_language_resolver: UserLanguageResolver | None = None
    translator: Translator = _identity_translator
    default_language: str = "ru"
    generic_error_key: str = "generic_error"
    generic_error_short_key: str = "generic_error_short"
    no_admin_rights_key: str = "no_admin_rights"


_fallback_dependencies = DecoratorDependencies()


def _get_dependencies() -> DecoratorDependencies:

    try:
        container = get_container()
    except RuntimeError:
        return _fallback_dependencies

    try:
        return container.get(DecoratorDependencies)
    except ValueError:
        deps = DecoratorDependencies()
        container.register_singleton(DecoratorDependencies, deps)
        return deps


def configure_decorators(
    *,
    spam_service: Any | None = None,
    spam_service_provider: SpamServiceProvider | None = None,
    user_language_resolver: UserLanguageResolver | None = None,
    translator: Translator | None = None,
    default_language: str | None = None,
    message_keys: Dict[str, str] | None = None,
) -> None:
    """Configure dependencies used by decorator helpers."""

    deps = _get_dependencies()

    if spam_service is not None:
        deps.spam_service = spam_service
    if spam_service_provider is not None:
        deps.spam_service_provider = spam_service_provider
        if spam_service is None:
            deps.spam_service = None
    if user_language_resolver is not None:
        deps.user_language_resolver = user_language_resolver
    if translator is not None:
        deps.translator = translator
    if default_language:
        deps.default_language = default_language
    if message_keys:
        deps.generic_error_key = message_keys.get(
            "generic_error", deps.generic_error_key
        )
        deps.generic_error_short_key = message_keys.get(
            "generic_error_short", deps.generic_error_short_key
        )
        deps.no_admin_rights_key = message_keys.get(
            "no_admin_rights", deps.no_admin_rights_key
        )


def reset_decorator_configuration() -> None:
    """Reset decorator dependencies to their defaults."""

    deps = _get_dependencies()

    deps.spam_service = None
    deps.spam_service_provider = None
    deps.user_language_resolver = None
    deps.translator = _identity_translator
    deps.default_language = "ru"
    deps.generic_error_key = "generic_error"
    deps.generic_error_short_key = "generic_error_short"
    deps.no_admin_rights_key = "no_admin_rights"


def _get_spam_service() -> Optional[Any]:

    deps = _get_dependencies()

    if deps.spam_service is not None:
        return deps.spam_service

    if deps.spam_service_provider is None:
        logger.debug("Spam service provider not configured; skipping spam check")
        return None

    try:
        service = deps.spam_service_provider()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to resolve spam protection service: %s", exc)
        service = None

    deps.spam_service = service
    return service


async def _resolve_user_language(user_id: Any) -> str:
    deps = _get_dependencies()

    if deps.user_language_resolver is None:
        return deps.default_language

    try:
        language = await deps.user_language_resolver(int(user_id))
        if not language:
            return deps.default_language
        return language
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Could not resolve user language for spam check (%s)", exc)
        return deps.default_language


def _translate(key: str, lang: str, **kwargs: Any) -> str:
    deps = _get_dependencies()
    try:
        return deps.translator(key, lang, **kwargs)
    except Exception:  # pragma: no cover - defensive fallback
        return key


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

        user_lang = await _resolve_user_language(user_id)

        service = _get_spam_service()
        try:
            if service is None:
                is_spam, reason = False, None
            else:
                is_spam, reason = await service.is_spam(
                    user_id,
                    message_text,
                    count_request=count_request,
                    user_lang=user_lang,
                )
        except Exception as exc:
            logger.warning("Spam check failed, proceeding: %s", exc)
            is_spam, reason = False, None

        if is_spam:
            logger.warning("Spam from user %s: %s", user_id, reason)

            if reason != "SILENT_BLOCK":
                try:
                    if getattr(update, "message", None):
                        await update.message.reply_text(reason)
                    elif getattr(update, "callback_query", None):
                        await update.callback_query.answer(
                            f"⚠️ {reason}", show_alert=True
                        )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to send spam warning message: %s", exc)

            return

        try:
            return await handler(update, context, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error in handler %s: %s", handler.__name__, exc)

            deps = _get_dependencies()
            try:
                if getattr(update, "message", None):
                    await update.message.reply_text(
                        _translate(deps.generic_error_key, user_lang)
                    )
                elif getattr(update, "callback_query", None):
                    await update.callback_query.answer(
                        _translate(deps.generic_error_short_key, user_lang),
                        show_alert=True,
                    )
            except Exception as inner:  # pragma: no cover - defensive logging
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
                    "Unauthorized attempt to access admin command by %s", user_id
                )
                user_lang = await _resolve_user_language(user_id or 0)
                deps = _get_dependencies()
                try:
                    if update.message:
                        await update.message.reply_text(
                            _translate(deps.no_admin_rights_key, user_lang)
                        )
                    elif update.callback_query:
                        await update.callback_query.answer(
                            _translate(deps.no_admin_rights_key, user_lang),
                            show_alert=True,
                        )
                except Exception as send_err:  # pragma: no cover - defensive logging
                    logger.debug(
                        "Failed to send no_admin_rights message to %s: %s",
                        user_id,
                        send_err,
                    )
                return
            return await handler(update, context, *args, **kwargs)

        return wrapper

    return decorator
