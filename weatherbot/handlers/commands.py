import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram import Bot, Update
from telegram.ext import ContextTypes

from weatherbot.application.interfaces import (
    ConversationStateStoreProtocol,
    UserServiceProtocol,
)
from weatherbot.core.decorators import spam_check
from weatherbot.core.exceptions import ValidationError
from weatherbot.domain.conversation import ConversationMode
from weatherbot.handlers.command_types import CommandArgs, normalize_command_args
from weatherbot.presentation.command_presenter import (
    CommandPresenter,
    KeyboardView,
    PresenterResponse,
)
from weatherbot.presentation.i18n import Localization, i18n
from weatherbot.presentation.keyboards import language_keyboard, main_keyboard
from weatherbot.presentation.subscription_presenter import SubscriptionPresenter
from weatherbot.presentation.telegram.command_menu import set_commands_for_chat
from weatherbot.presentation.validation import (
    SubscribeTimeModel,
    validate_payload,
)

logger = logging.getLogger(__name__)


QuotaNotifier = Callable[[object], Awaitable[None]]
ScheduleSubscription = Callable[[object, int, int, int], Awaitable[None]]


@dataclass
class CommandHandlerDependencies:
    command_presenter: CommandPresenter
    subscription_presenter: SubscriptionPresenter
    user_service: UserServiceProtocol
    state_store: ConversationStateStoreProtocol
    quota_notifier: QuotaNotifier
    schedule_subscription: ScheduleSubscription
    bot: Bot
    localization: Localization


_deps: CommandHandlerDependencies | None = None


def configure_command_handlers(deps: CommandHandlerDependencies) -> None:
    global _deps
    _deps = deps


def _require_deps() -> CommandHandlerDependencies:
    if _deps is None:
        raise RuntimeError("Command handler dependencies are not configured")
    return _deps


def get_user_service() -> UserServiceProtocol:
    return _require_deps().user_service


def get_conversation_state_store() -> ConversationStateStoreProtocol:
    return _require_deps().state_store


async def notify_quota_if_needed(bot) -> None:
    await _require_deps().quota_notifier(bot)


async def schedule_daily_timezone_aware(
    job_queue, chat_id: int, hour: int, minute: int
) -> None:
    await _require_deps().schedule_subscription(job_queue, chat_id, hour, minute)


def __subscription_presenter() -> SubscriptionPresenter:
    return _require_deps().subscription_presenter


def __command_presenter() -> CommandPresenter:
    return _require_deps().command_presenter


def __keyboard_from_response(response: PresenterResponse):
    if response.keyboard is KeyboardView.MAIN:
        return main_keyboard(response.language)
    if response.keyboard is KeyboardView.LANGUAGE:
        return language_keyboard()
    return None


@spam_check
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.start(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )

        # Update command menu for this chat with the user's language
        deps = _require_deps()
        user_lang = result.language or "ru"
        try:
            await set_commands_for_chat(deps.bot, chat_id, user_lang, deps.localization)
            logger.debug(f"Commands set for chat {chat_id} in language '{user_lang}'")
        except Exception as e:
            logger.warning(f"Failed to set commands for chat {chat_id}: {e}")

    except Exception:
        logger.exception("Error in /start command")
        user_lang = (
            await get_user_service().get_user_language(str(update.effective_chat.id))
            if "update" in locals() and update.effective_chat
            else "ru"
        )
        await update.message.reply_text(i18n.get("generic_error", user_lang))


@spam_check
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.help(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /help command")
        user_lang = (
            await get_user_service().get_user_language(str(update.effective_chat.id))
            if "update" in locals() and update.effective_chat
            else "ru"
        )
        await update.message.reply_text(i18n.get("generic_error", user_lang))


@spam_check
async def sethome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        args: CommandArgs = normalize_command_args(context.args)
        presenter = __command_presenter()
        city_input = " ".join(args) if args else None
        result = await presenter.set_home(chat_id, city_input)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /sethome command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        text = i18n.get(
            "sethome_failed",
            user_lang,
            city=(
                city_input
                if "city_input" in locals() and city_input
                else "unknown city"
            ),
        )
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))


@spam_check
async def home_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.home_weather(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
        if result.notify_quota:
            await notify_quota_if_needed(context.bot)
    except Exception:
        logger.exception("Error in /home command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        text = i18n.get("weather_error", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))


@spam_check
async def unsethome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.unset_home(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /unsethome command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        args: CommandArgs = normalize_command_args(context.args)
        presenter = __subscription_presenter()

        if not args:
            result = await presenter.prompt_for_time(chat_id)
            await update.message.reply_text(
                result.message, reply_markup=main_keyboard(result.language)
            )
            return

        payload = validate_payload(SubscribeTimeModel, time=args[0])
        result = await presenter.subscribe(
            chat_id,
            payload.time,
            validate_input=False,
        )

        await update.message.reply_text(
            result.message, reply_markup=main_keyboard(result.language)
        )

        if (
            result.success
            and result.schedule
            and context.application
            and context.application.job_queue
        ):
            import asyncio

            asyncio.create_task(
                schedule_daily_timezone_aware(
                    context.application.job_queue,
                    chat_id,
                    result.schedule.hour,
                    result.schedule.minute,
                )
            )
    except ValidationError as e:
        logger.warning(f"Validation error in /subscribe: {e}")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        # Check if it's home location error and use appropriate message
        if "Home location must be set" in str(e):
            error_message = i18n.get("subscribe_home_required", user_lang)
        else:
            error_message = str(e)
        await update.message.reply_text(
            error_message, reply_markup=main_keyboard(user_lang)
        )
    except Exception:
        logger.exception("Error in /subscribe command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        text = i18n.get("subscribe_error", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))


@spam_check
async def unsubscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __subscription_presenter()
        result = await presenter.unsubscribe(chat_id)

        if context.application and context.application.job_queue:
            jobs = context.application.job_queue.get_jobs_by_name(
                f"daily_weather_{chat_id}"
            )
            for job in jobs:
                job.schedule_removal()
        await update.message.reply_text(
            result.message, reply_markup=main_keyboard(result.language)
        )
    except Exception:
        logger.exception("Error in /unsubscribe command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    chat_id = update.effective_chat.id
    user_service = get_user_service()
    user_lang = await user_service.get_user_language(str(chat_id))
    cancelled = False

    state_store = get_conversation_state_store()
    current_state = state_store.get_state(chat_id)
    if current_state.mode != ConversationMode.IDLE:
        state_store.clear_conversation(chat_id)
        cancelled = True
    if cancelled:
        text = i18n.get("operation_cancelled", user_lang)
    else:
        text = i18n.get("unknown_command", user_lang)
    await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))


@spam_check
async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        user_service = get_user_service()

        user_lang = await user_service.get_user_language(str(chat_id))

        args: CommandArgs = normalize_command_args(context.args)
        if args:
            language_code = parse_language_input(args[0])
            if language_code:
                await user_service.set_user_language(str(chat_id), language_code)

                lang_names = {"en": "English", "ru": "Русский", "de": "Deutsch"}
                language_name = lang_names.get(language_code, language_code)

                text = i18n.get(
                    "language_changed", language_code, language=language_name
                )
                await update.message.reply_text(
                    text, reply_markup=main_keyboard(language_code)
                )
                return
            else:
                text = i18n.get("language_usage", user_lang)
                await update.message.reply_text(
                    text, reply_markup=main_keyboard(user_lang)
                )
                return

        language_header = i18n.get("language_selection_header", user_lang)
        language_instructions = i18n.get("language_selection_instructions", user_lang)
        multilang_text = language_header + language_instructions

        get_conversation_state_store().set_awaiting_mode(
            chat_id, ConversationMode.AWAITING_LANGUAGE_INPUT
        )
        await update.message.reply_text(
            multilang_text, reply_markup=main_keyboard(user_lang)
        )
    except ValidationError as e:
        logger.warning(f"Validation error in /language: {e}")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(str(e), reply_markup=main_keyboard(user_lang))
    except Exception:
        logger.exception("Error in /language command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def data_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.data_snapshot(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /data command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def delete_me_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.delete_user_data(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /delete_me command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        result = await presenter.privacy(chat_id)
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /privacy command")
        user_lang = (
            await get_user_service().get_user_language(str(update.effective_chat.id))
            if "update" in locals() and update.effective_chat
            else "ru"
        )
        await update.message.reply_text(i18n.get("generic_error", user_lang))


@spam_check
async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        presenter = __command_presenter()
        user = update.effective_user
        result = await presenter.whoami(
            chat_id,
            user_id=user.id,
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            username=getattr(user, "username", None),
        )
        await update.message.reply_text(
            result.message,
            reply_markup=__keyboard_from_response(result),
            parse_mode=result.parse_mode,
        )
    except Exception:
        logger.exception("Error in /whoami command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("generic_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


@spam_check
async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info(f"/weather command from user {update.effective_chat.id}")
    try:
        chat_id = update.effective_chat.id
        user_lang = await get_user_service().get_user_language(str(chat_id))

        get_conversation_state_store().set_awaiting_mode(
            chat_id, ConversationMode.AWAITING_CITY_WEATHER
        )
        await update.message.reply_text(
            i18n.get("enter_city", user_lang),
            reply_markup=main_keyboard(user_lang),
        )
    except Exception:
        logger.exception("Error in /weather command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(
            i18n.get("weather_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )


def parse_language_input(user_input: str) -> str | None:

    user_input = user_input.strip().lower()

    if user_input in ["ru", "en", "de"]:
        return user_input

    flag_map = {"🇷🇺": "ru", "🇺🇸": "en", "🇬🇧": "en", "🇩🇪": "de"}
    if user_input in flag_map:
        return flag_map[user_input]

    language_names = {
        "русский": "ru",
        "russian": "ru",
        "english": "en",
        "deutsch": "de",
        "german": "de",
        "немецкий": "de",
    }
    if user_input in language_names:
        return language_names[user_input]
    return None
