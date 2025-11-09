import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.__version__ import (
    __release_date__,
    __supported_languages__,
    __version__,
)
from weatherbot.application.interfaces import (
    ConversationStateStoreProtocol,
    UserServiceProtocol,
    WeatherApplicationServiceProtocol,
)
from weatherbot.core.decorators import spam_check
from weatherbot.core.exceptions import (
    GeocodeServiceError,
    StorageError,
    ValidationError,
    WeatherQuotaExceededError,
    WeatherServiceError,
)
from weatherbot.domain.conversation import ConversationMode
from weatherbot.handlers.commands import parse_language_input
from weatherbot.presentation.i18n import i18n
from weatherbot.presentation.keyboards import (
    BTN_LANGUAGE,
    main_keyboard,
)
from weatherbot.presentation.subscription_presenter import SubscriptionPresenter
from weatherbot.presentation.validation import (
    CityInputModel,
    SubscribeTimeModel,
    validate_payload,
)
from weatherbot.utils.text import matches_button
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


# Type aliases for dependency injection
QuotaNotifier = Callable[[object], Awaitable[None]]
ScheduleSubscription = Callable[[object, int, int, int], Awaitable[None]]
WeatherFormatter = Callable[..., str]


@dataclass
class MessageHandlerDependencies:
    user_service: UserServiceProtocol
    weather_service: WeatherApplicationServiceProtocol
    state_store: ConversationStateStoreProtocol
    subscription_presenter: SubscriptionPresenter
    quota_notifier: QuotaNotifier
    schedule_subscription: ScheduleSubscription
    weather_formatter: WeatherFormatter


_deps: MessageHandlerDependencies | None = None


def configure_message_handlers(deps: MessageHandlerDependencies) -> None:
    global _deps
    _deps = deps


def _require_deps() -> MessageHandlerDependencies:
    if _deps is None:
        raise RuntimeError("Message handler dependencies are not configured")
    return _deps


def get_user_service() -> UserServiceProtocol:
    return _require_deps().user_service


def get_weather_application_service() -> WeatherApplicationServiceProtocol:
    return _require_deps().weather_service


def get_conversation_state_store() -> ConversationStateStoreProtocol:
    return _require_deps().state_store


def get_subscription_presenter() -> SubscriptionPresenter:
    return _require_deps().subscription_presenter


async def notify_quota_if_needed(bot) -> None:
    await _require_deps().quota_notifier(bot)


async def schedule_daily_timezone_aware(
    job_queue, chat_id: int, hour: int, minute: int
) -> None:
    await _require_deps().schedule_subscription(job_queue, chat_id, hour, minute)


def format_weather(*args, **kwargs):
    return _require_deps().weather_formatter(*args, **kwargs)


@spam_check
async def on_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    loc = update.message.location
    lat, lon = loc.latitude, loc.longitude
    chat_id = update.effective_chat.id
    try:
        user_service = get_user_service()
        weather_service = get_weather_application_service()
        state_store = get_conversation_state_store()

        user_lang = await user_service.get_user_language(str(chat_id))
        state_store.set_location(chat_id, lat, lon)
        weather_data = await weather_service.get_weather_by_coordinates(lat, lon)
        msg = format_weather(weather_data, lang=user_lang)
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=main_keyboard(user_lang)
        )
        await notify_quota_if_needed(context.bot)

    except WeatherQuotaExceededError as e:
        profile = await user_service.get_user_profile(str(chat_id))
        tz_name = profile.home.timezone if profile.home else None
        reset_text = format_reset_time(e.reset_at, tz_name)
        await update.message.reply_text(
            i18n.get("weather_quota_exceeded", user_lang, reset_time=reset_text),
            reply_markup=main_keyboard(user_lang),
        )
        await notify_quota_if_needed(context.bot)

    except (WeatherServiceError, ValidationError) as e:
        logger.error(f"Error getting weather by coordinates for {chat_id}: {e}")
        user_lang = (
            await user_service.get_user_language(str(chat_id))
            if "user_service" in locals()
            else "ru"
        )
        await update.message.reply_text(
            i18n.get("weather_error", user_lang),
            reply_markup=main_keyboard(user_lang),
        )
    except Exception:
        logger.exception(f"Unexpected error handling location for {chat_id}")
        user_lang = await user_service.get_user_language(str(chat_id))
        await update.message.reply_text(
            i18n.get("generic_error", user_lang), reply_markup=main_keyboard(user_lang)
        )


@spam_check
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    text = update.message.text
    if not text:  # Guard against None or empty text
        return

    chat_id = update.effective_chat.id
    user_service = get_user_service()
    weather_service = get_weather_application_service()
    state_store = get_conversation_state_store()
    subscription_presenter = get_subscription_presenter()

    try:
        user_lang = await user_service.get_user_language(str(chat_id))

        if text.strip().lower() == "/cancel":
            current_state = state_store.get_state(chat_id)
            if current_state.mode != ConversationMode.IDLE:
                state_store.clear_conversation(chat_id)
                # Legacy compatibility cleanup
                await update.message.reply_text(
                    i18n.get("operation_cancelled", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
                return

        # To handle keyboard caching issues after language changes,
        # check button text against all supported languages
        SUPPORTED_LANGUAGES = ["ru", "en", "de"]

        def matches_button_any_lang(text: str, button_key: str) -> bool:
            """Check if text matches button in any supported language."""
            return any(
                matches_button(text, i18n.get(button_key, lang))
                for lang in SUPPORTED_LANGUAGES
            )

        is_help_button = matches_button_any_lang(text, "help_button")
        is_weather_city_button = matches_button_any_lang(text, "weather_city_button")
        is_weather_home_button = matches_button_any_lang(text, "weather_home_button")
        is_set_home_button = matches_button_any_lang(text, "set_home_button")
        is_unset_home_button = matches_button_any_lang(text, "remove_home_button")

        if state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME):
            state_store.clear_conversation(chat_id)
            try:
                payload = validate_payload(SubscribeTimeModel, time=text)
                result = await subscription_presenter.subscribe(
                    chat_id,
                    payload.time,
                    clear_state=False,
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
                if "Home location must be set" in str(e):
                    error_message = i18n.get("subscribe_home_required", user_lang)
                else:
                    error_message = str(e)
                await update.message.reply_text(
                    error_message, reply_markup=main_keyboard(user_lang)
                )
            except Exception:
                logger.exception(f"Error during subscription for {chat_id}")
                await update.message.reply_text(
                    i18n.get("subscribe_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            return

        if state_store.is_awaiting(chat_id, ConversationMode.AWAITING_LANGUAGE_INPUT):
            state_store.clear_conversation(chat_id)
            try:
                new_language = parse_language_input(text)
                if new_language is None:
                    message = i18n.get("language_not_recognized", user_lang)
                    await update.message.reply_text(
                        message,
                        parse_mode="HTML",
                        reply_markup=main_keyboard(user_lang),
                    )
                    return

                await user_service.set_user_language(str(chat_id), new_language)

                lang_names = {"en": "English", "ru": "Русский", "de": "Deutsch"}
                language_name = lang_names.get(new_language, new_language)

                await update.message.reply_text(
                    i18n.get("language_changed", new_language, language=language_name),
                    reply_markup=main_keyboard(new_language),
                )
            except Exception:
                logger.exception(f"Error changing language for {chat_id}")
                await update.message.reply_text(
                    i18n.get("language_change_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            return

        if state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SETHOME):
            state_store.clear_conversation(chat_id)
            try:
                last_location = state_store.get_last_location(chat_id)
                if last_location:
                    lat, lon = last_location
                    await user_service.set_user_home(str(chat_id), lat, lon, text)
                    await update.message.reply_text(
                        i18n.get(
                            "sethome_success",
                            user_lang,
                            location=text,
                            lat=lat,
                            lon=lon,
                        ),
                        reply_markup=main_keyboard(user_lang),
                    )
                    return

                geocode_result = await weather_service.geocode_city(text)
                if not geocode_result:
                    raise GeocodeServiceError("not found")
                lat = geocode_result.lat
                lon = geocode_result.lon
                label = geocode_result.label or text
                await user_service.set_user_home(str(chat_id), lat, lon, label)
                await update.message.reply_text(
                    i18n.get(
                        "sethome_success",
                        user_lang,
                        location=label or text,
                        lat=lat,
                        lon=lon,
                    ),
                    reply_markup=main_keyboard(user_lang),
                )
                return
            except GeocodeServiceError:
                await update.message.reply_text(
                    i18n.get("city_not_found", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
                return
            except (ValidationError, StorageError) as e:
                logger.error(f"Error setting home for {chat_id}: {e}")
                await update.message.reply_text(
                    i18n.get("set_home_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
                return

        if state_store.is_awaiting(chat_id, ConversationMode.AWAITING_CITY_WEATHER):
            state_store.clear_conversation(chat_id)
            try:
                payload = validate_payload(CityInputModel, city=text)
                weather_result = await weather_service.get_weather_by_city(payload.city)
                report = weather_result.report
                place_label = weather_result.location.label or payload.city
                msg = format_weather(report, place_label=place_label, lang=user_lang)
                await update.message.reply_text(
                    msg, parse_mode="HTML", reply_markup=main_keyboard(user_lang)
                )
                await notify_quota_if_needed(context.bot)
            except GeocodeServiceError:
                await update.message.reply_text(
                    i18n.get("city_not_found", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            except WeatherQuotaExceededError as e:
                home = await user_service.get_user_home(str(chat_id))
                tz_name = home.timezone if home else None
                reset_text = format_reset_time(e.reset_at, tz_name)
                await update.message.reply_text(
                    i18n.get(
                        "weather_quota_exceeded", user_lang, reset_time=reset_text
                    ),
                    reply_markup=main_keyboard(user_lang),
                )
                await notify_quota_if_needed(context.bot)
            except (ValidationError, WeatherServiceError) as e:
                logger.error(
                    f"Error getting weather for city {text}, user {chat_id}: {e}"
                )
                await update.message.reply_text(
                    i18n.get("weather_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            return

        if is_weather_home_button:
            home = None
            try:
                home = await user_service.get_user_home(str(chat_id))
                if not home:
                    raise ValidationError("Home not set")
                weather_data = await weather_service.get_weather_by_coordinates(
                    home.lat, home.lon
                )
                msg = format_weather(
                    weather_data, place_label=home.label, lang=user_lang
                )
                await update.message.reply_text(
                    msg, parse_mode="HTML", reply_markup=main_keyboard(user_lang)
                )
                await notify_quota_if_needed(context.bot)
            except WeatherQuotaExceededError as e:
                tz_name = home.timezone if home else None
                reset_text = format_reset_time(e.reset_at, tz_name)
                await update.message.reply_text(
                    i18n.get(
                        "weather_quota_exceeded", user_lang, reset_time=reset_text
                    ),
                    reply_markup=main_keyboard(user_lang),
                )
                await notify_quota_if_needed(context.bot)
            except ValidationError:
                await update.message.reply_text(
                    i18n.get("home_not_set", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            except (StorageError, WeatherServiceError) as e:
                logger.error(f"Error getting home weather for {chat_id}: {e}")
                await update.message.reply_text(
                    i18n.get("weather_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )

        elif is_weather_city_button:
            state_store.set_awaiting_mode(
                chat_id, ConversationMode.AWAITING_CITY_WEATHER
            )
            await update.message.reply_text(
                i18n.get("enter_city", user_lang),
                reply_markup=main_keyboard(user_lang),
            )

        elif is_set_home_button:
            state_store.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)
            await update.message.reply_text(
                i18n.get("enter_home_city", user_lang),
                reply_markup=main_keyboard(user_lang),
            )
            return

        elif is_unset_home_button:
            try:
                removed = await user_service.remove_user_home(str(chat_id))
                if removed:
                    await update.message.reply_text(
                        i18n.get("home_unset", user_lang),
                        reply_markup=main_keyboard(user_lang),
                    )
                else:
                    await update.message.reply_text(
                        i18n.get("home_not_set", user_lang),
                        reply_markup=main_keyboard(user_lang),
                    )
            except Exception:
                logger.exception(f"Error removing home for {chat_id}")
                await update.message.reply_text(
                    i18n.get("unset_home_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )

        elif is_help_button:
            help_text = i18n.get(
                "help_message",
                user_lang,
                version=__version__,
                release_date=__release_date__,
                languages=__supported_languages__,
            )
            await update.message.reply_text(
                help_text, reply_markup=main_keyboard(user_lang)
            )

        elif matches_button(text, BTN_LANGUAGE):
            from weatherbot.handlers.commands import language_cmd

            await language_cmd.__wrapped__(update, context)

        else:
            try:
                payload = validate_payload(CityInputModel, city=text)
                weather_result = await weather_service.get_weather_by_city(payload.city)
                place_label = weather_result.location.label or payload.city
                msg = format_weather(
                    weather_result.report, place_label=place_label, lang=user_lang
                )
                await update.message.reply_text(
                    msg, parse_mode="HTML", reply_markup=main_keyboard(user_lang)
                )
            except GeocodeServiceError:
                await update.message.reply_text(
                    i18n.get("unknown_command", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
            except WeatherQuotaExceededError as e:
                profile = await user_service.get_user_profile(str(chat_id))
                tz_name = profile.home.timezone if profile.home else None
                reset_text = format_reset_time(e.reset_at, tz_name)
                await update.message.reply_text(
                    i18n.get(
                        "weather_quota_exceeded", user_lang, reset_time=reset_text
                    ),
                    reply_markup=main_keyboard(user_lang),
                )
                await notify_quota_if_needed(context.bot)
            except (ValidationError, WeatherServiceError) as e:
                logger.error(f"Error getting weather for {text}, user {chat_id}: {e}")
                await update.message.reply_text(
                    i18n.get("weather_error", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )

    except Exception:
        logger.exception(f"Unexpected error handling text '{text}' for {chat_id}")
        try:
            user_lang = await user_service.get_user_language(str(chat_id))
        except Exception:
            user_lang = "ru"
        await update.message.reply_text(
            i18n.get("generic_error", user_lang), reply_markup=main_keyboard(user_lang)
        )
