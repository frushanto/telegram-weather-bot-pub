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
    ValidationError,
    WeatherServiceError,
)
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
)
from weatherbot.jobs.scheduler import schedule_daily
from weatherbot.presentation.formatter import format_weather
from weatherbot.presentation.i18n import i18n
from weatherbot.presentation.keyboards import language_keyboard, main_keyboard

logger = logging.getLogger(__name__)


@spam_check
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        user_data = await user_service.get_user_data(str(chat_id))
        if not user_data or "language" not in user_data:
            multilingual_text = (
                "Hello! Привет! Hallo! 🌍\n\n"
                "I'm a weather bot that supports multiple languages.\n"
                "Я погодный бот с поддержкой нескольких языков.\n"
                "Ich bin ein Wetter-Bot mit Unterstützung für mehrere Sprachen.\n\n"
                "🌐 Please choose your language:\n"
                "🌐 Пожалуйста, выберите свой язык:\n"
                "🌐 Bitte wählen Sie Ihre Sprache:"
            )
            await update.message.reply_text(
                multilingual_text, reply_markup=language_keyboard()
            )
        else:
            text = i18n.get("start_message", user_lang)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))
        text = i18n.get(
            "help_message",
            user_lang,
            version=__version__,
            release_date=__release_date__,
            languages=__supported_languages__,
        )
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        args = context.args
        if not args:

            user_service = get_user_service()
            user_lang = await user_service.get_user_language(str(chat_id))
            awaiting_sethome[chat_id] = True

            text = i18n.get("sethome_prompt", user_lang)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
            return

        user_service = get_user_service()
        weather_service = get_weather_application_service()
        user_lang = await user_service.get_user_language(str(chat_id))
        city = " ".join(args)

        geocode_result = await weather_service.geocode_city(city)
        if not geocode_result:
            text = i18n.get("sethome_failed", user_lang, city=city)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
            return
        lat, lon, label = geocode_result

        await user_service.set_user_home(str(chat_id), lat, lon, label)
        text = i18n.get("sethome_success", user_lang, location=label, lat=lat, lon=lon)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
    except (ValidationError, GeocodeServiceError) as e:
        logger.warning(f"Validation error in /sethome: {e}")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(str(e), reply_markup=main_keyboard(user_lang))
    except Exception:
        logger.exception("Error in /sethome command")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        text = i18n.get(
            "sethome_failed",
            user_lang,
            city=city if "city" in locals() else "unknown city",
        )
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))


@spam_check
async def home_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        chat_id = update.effective_chat.id
        user_service = get_user_service()
        weather_service = get_weather_application_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        home = await user_service.get_user_home(str(chat_id))
        if not home:
            text = i18n.get("home_not_set", user_lang)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
            return

        weather_data = await weather_service.get_weather_by_coordinates(
            home["lat"], home["lon"]
        )

        msg = format_weather(
            weather_data, place_label=home.get("label"), lang=user_lang
        )
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=main_keyboard(user_lang)
        )
    except WeatherServiceError as e:
        logger.warning(f"Weather service error in /home: {e}")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        text = i18n.get("weather_error", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        removed = await user_service.remove_user_home(str(chat_id))
        if removed:
            text = i18n.get("home_removed", user_lang)
        else:
            text = i18n.get("home_not_set", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        args = context.args

        if not args:
            user_service = get_user_service()
            user_lang = await user_service.get_user_language(str(chat_id))
            awaiting_subscribe_time[chat_id] = True
            text = i18n.get("subscribe_prompt", user_lang)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
            return

        user_service = get_user_service()
        subscription_service = get_subscription_service()
        user_lang = await user_service.get_user_language(str(chat_id))
        time_str = args[0]

        hour, minute = await subscription_service.parse_time_string(time_str)

        await subscription_service.set_subscription(str(chat_id), hour, minute)

        if context.application and context.application.job_queue:
            schedule_daily(context.application.job_queue, chat_id, hour, minute)
        text = i18n.get("subscribe_success", user_lang, hour=hour, minute=minute)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
    except ValidationError as e:
        logger.warning(f"Validation error in /subscribe: {e}")
        user_lang = await get_user_service().get_user_language(
            str(update.effective_chat.id)
        )
        await update.message.reply_text(str(e), reply_markup=main_keyboard(user_lang))
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
        user_service = get_user_service()
        subscription_service = get_subscription_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        removed = await subscription_service.remove_subscription(str(chat_id))

        if context.application and context.application.job_queue:
            jobs = context.application.job_queue.get_jobs_by_name(
                f"daily_weather_{chat_id}"
            )
            for job in jobs:
                job.schedule_removal()
        if removed:
            text = i18n.get("unsubscribe_success", user_lang)
        else:
            text = i18n.get("not_subscribed", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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

    for state in (
        awaiting_sethome,
        awaiting_subscribe_time,
        awaiting_city_weather,
        awaiting_language_input,
    ):
        if chat_id in state:
            state.pop(chat_id, None)
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

        args = context.args
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

        awaiting_language_input[chat_id] = True
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
        user_service = get_user_service()

        default_lang = await user_service.get_user_language(str(chat_id))
        user_data = await user_service.get_user_data(str(chat_id))

        user_lang = user_data.get("language", default_lang)
        if not user_data:
            text = i18n.get("no_data_stored", user_lang)
            await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
            return

        data_parts = []
        data_parts.append(f"💾 {i18n.get('your_data', user_lang)}:")
        if "lat" in user_data and "lon" in user_data:
            home_label = user_data.get("label", i18n.get("unknown_location", user_lang))
            data_parts.append(f"🏠 {i18n.get('home_address', user_lang)}: {home_label}")
            data_parts.append(
                f"📍 {i18n.get('coordinates', user_lang)}: {user_data['lat']:.4f}, {user_data['lon']:.4f}"
            )
        if "sub_hour" in user_data:
            hour = user_data["sub_hour"]
            minute = user_data.get("sub_min", 0)
            data_parts.append(
                f"🔔 {i18n.get('subscription', user_lang)}: {hour:02d}:{minute:02d}"
            )
        if "language" in user_data:
            data_parts.append(
                f"🌐 {i18n.get('language', user_lang)}: {user_data['language']}"
            )
        text = "\n".join(data_parts)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        deleted = await user_service.delete_user_data(str(chat_id))
        if deleted:
            text = i18n.get("data_deleted", user_lang)
        else:
            text = i18n.get("no_data_to_delete", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard("ru"))
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
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))
        text = i18n.get("privacy_message", user_lang)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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
        user_service = get_user_service()
        user_lang = await user_service.get_user_language(str(chat_id))

        user = update.effective_user
        info_parts = []
        info_parts.append(f"👤 {i18n.get('user_info', user_lang)}:")
        info_parts.append(f"🆔 ID: {user.id}")
        if user.first_name:
            info_parts.append(
                f"👤 {i18n.get('first_name', user_lang)}: {user.first_name}"
            )
        if user.last_name:
            info_parts.append(
                f"👤 {i18n.get('last_name', user_lang)}: {user.last_name}"
            )
        if user.username:
            info_parts.append(f"📝 {i18n.get('username', user_lang)}: @{user.username}")
        info_parts.append(f"💬 {i18n.get('chat_id', user_lang)}: {chat_id}")
        info_parts.append(f"🌐 {i18n.get('language', user_lang)}: {user_lang}")
        text = "\n".join(info_parts)
        await update.message.reply_text(text, reply_markup=main_keyboard(user_lang))
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

        from weatherbot.handlers.messages import awaiting_city_weather

        awaiting_city_weather[chat_id] = True

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
