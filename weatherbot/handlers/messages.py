import logging

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot.__version__ import (
    __release_date__,
    __supported_languages__,
    __version__,
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
from weatherbot.infrastructure.quota_notifications import notify_quota_if_needed
from weatherbot.infrastructure.setup import (
    get_subscription_service,
    get_user_service,
    get_weather_application_service,
)
from weatherbot.infrastructure.state import (
    awaiting_city_weather,
    awaiting_language_input,
    awaiting_sethome,
    awaiting_subscribe_time,
    conversation_manager,
    last_location_by_chat,
)
from weatherbot.jobs.scheduler import schedule_daily_timezone_aware
from weatherbot.presentation.formatter import format_weather
from weatherbot.presentation.i18n import i18n
from weatherbot.presentation.keyboards import (
    BTN_LANGUAGE,
    main_keyboard,
)
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


@spam_check
async def on_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    loc = update.message.location
    lat, lon = loc.latitude, loc.longitude
    chat_id = update.effective_chat.id
    try:
        user_service = get_user_service()
        weather_service = get_weather_application_service()

        user_lang = await user_service.get_user_language(str(chat_id))
        conversation_manager.set_location(chat_id, lat, lon)
        last_location_by_chat[chat_id] = (lat, lon)  # Legacy compatibility

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
    chat_id = update.effective_chat.id
    try:
        try:
            user_service = get_user_service()
            weather_service = get_weather_application_service()
            user_lang = await user_service.get_user_language(str(chat_id))
        except Exception:

            user_service = None
            weather_service = None
            user_lang = "ru"

        if text.strip().lower() == "/cancel":
            current_state = conversation_manager.get_state(chat_id)
            if current_state.mode != ConversationMode.IDLE:
                conversation_manager.clear_conversation(chat_id)
                # Legacy compatibility cleanup
                awaiting_sethome.pop(chat_id, None)
                awaiting_subscribe_time.pop(chat_id, None)
                awaiting_city_weather.pop(chat_id, None)
                awaiting_language_input.pop(chat_id, None)

                await update.message.reply_text(
                    i18n.get("operation_cancelled", user_lang),
                    reply_markup=main_keyboard(user_lang),
                )
                return

        weather_city_label = i18n.get("weather_city_button", user_lang)
        weather_home_label = i18n.get("weather_home_button", user_lang)
        set_home_label = i18n.get("set_home_button", user_lang)
        unset_home_label = i18n.get("remove_home_button", user_lang)
        help_label = i18n.get("help_button", user_lang)

        if conversation_manager.is_awaiting(
            chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME
        ):
            conversation_manager.clear_conversation(chat_id)
            awaiting_subscribe_time.pop(chat_id, None)  # Legacy cleanup
            subscription_service = get_subscription_service()
            try:
                hour, minute = await subscription_service.parse_time_string(text)
                await subscription_service.set_subscription(str(chat_id), hour, minute)
                if context.application and context.application.job_queue:
                    import asyncio

                    asyncio.create_task(
                        schedule_daily_timezone_aware(
                            context.application.job_queue, chat_id, hour, minute
                        )
                    )
                await update.message.reply_text(
                    i18n.get("subscribe_success", user_lang, hour=hour, minute=minute),
                    reply_markup=main_keyboard(user_lang),
                )
            except ValidationError as e:
                # Check if it's home location error and use appropriate message
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

        if conversation_manager.is_awaiting(
            chat_id, ConversationMode.AWAITING_LANGUAGE_INPUT
        ):
            conversation_manager.clear_conversation(chat_id)
            awaiting_language_input.pop(chat_id, None)  # Legacy cleanup
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

        if conversation_manager.is_awaiting(chat_id, ConversationMode.AWAITING_SETHOME):
            conversation_manager.clear_conversation(chat_id)
            awaiting_sethome.pop(chat_id, None)  # Legacy cleanup
            try:
                last_location = conversation_manager.get_last_location(chat_id)
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
                else:
                    geocode_result = await weather_service.geocode_city(text)
                    if not geocode_result:
                        raise GeocodeServiceError("not found")
                    lat, lon, label = geocode_result
                    await user_service.set_user_home(
                        str(chat_id), lat, lon, label or text
                    )
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

        if conversation_manager.is_awaiting(
            chat_id, ConversationMode.AWAITING_CITY_WEATHER
        ):
            conversation_manager.clear_conversation(chat_id)
            awaiting_city_weather.pop(chat_id, None)  # Legacy cleanup
            try:
                weather_data, label = await weather_service.get_weather_by_city(text)
                msg = format_weather(
                    weather_data, place_label=label or text, lang=user_lang
                )
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

        if text == weather_home_label:
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
                tz_name = home.timezone if "home" in locals() and home else None
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

        elif text == weather_city_label:
            conversation_manager.set_awaiting_mode(
                chat_id, ConversationMode.AWAITING_CITY_WEATHER
            )
            awaiting_city_weather[chat_id] = True  # Legacy compatibility
            await update.message.reply_text(
                i18n.get("enter_city", user_lang),
                reply_markup=main_keyboard(user_lang),
            )

        elif text == set_home_label:
            conversation_manager.set_awaiting_mode(
                chat_id, ConversationMode.AWAITING_SETHOME
            )
            awaiting_sethome[chat_id] = True  # Legacy compatibility
            await update.message.reply_text(
                i18n.get("enter_home_city", user_lang),
                reply_markup=main_keyboard(user_lang),
            )
            return

        elif text == unset_home_label:
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

        elif text == help_label:
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

        elif text == BTN_LANGUAGE:
            from weatherbot.handlers.commands import language_cmd

            await language_cmd.__wrapped__(update, context)

        else:

            try:
                weather_data, label = await weather_service.get_weather_by_city(text)
                msg = format_weather(
                    weather_data, place_label=label or text, lang=user_lang
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
            user_lang = await get_user_service().get_user_language(str(chat_id))
        except Exception:
            user_lang = "ru"
        await update.message.reply_text(
            i18n.get("generic_error", user_lang), reply_markup=main_keyboard(user_lang)
        )
