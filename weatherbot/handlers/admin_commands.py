import logging

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot import __release_date__, __supported_languages__, __version__
from weatherbot.core.config import get_config
from weatherbot.core.decorators import admin_only
from weatherbot.infrastructure.setup import get_admin_service
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


@admin_only(get_config().admin_ids)
async def admin_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        stats = await get_admin_service().get_stats()
        lines = [
            f"📊 **{i18n.get('admin_stats_title', admin_lang)}**",
            f"{i18n.get('admin_total_users', admin_lang)}: {stats.user_count}",
            f"{i18n.get('admin_blocked_users', admin_lang)}: {stats.blocked_count}",
            "",
        ]
        if stats.top_users:
            lines.append(f"🔥 **{i18n.get('admin_top_users', admin_lang)}:**")
            for index, top_user in enumerate(stats.top_users, start=1):
                blocked_suffix = " 🚫" if top_user.is_blocked else ""
                lines.append(
                    f"{index}. ID {top_user.user_id}: {top_user.daily_requests} "
                    f"{i18n.get('admin_requests_today', admin_lang)}{blocked_suffix}"
                )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Error in admin_stats_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_stats", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        args = context.args
        if not args:
            await update.message.reply_text(i18n.get("admin_unblock_usage", admin_lang))
            return
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                i18n.get("admin_invalid_user_id", admin_lang)
            )
            return
        success = await get_admin_service().unblock_user(user_id)
        if success:
            await update.message.reply_text(
                f"✅ {i18n.get('admin_user_unblocked', admin_lang, user_id=user_id)}"
            )
        else:
            await update.message.reply_text(
                f"❌ {i18n.get('admin_user_not_found', admin_lang, user_id=user_id)}"
            )
    except Exception as e:
        logger.exception(f"Error in admin_unblock_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_unblock", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_user_info_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                i18n.get("admin_user_info_usage", admin_lang)
            )
            return
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                i18n.get("admin_invalid_user_id", admin_lang)
            )
            return

        info = await get_admin_service().get_user_info(user_id)
        lines = [
            f"👤 **{i18n.get('admin_user_info_title', admin_lang, user_id=user_id)}:**",
            f"{i18n.get('admin_user_requests_today', admin_lang)}: {info.requests_today}",
        ]
        blocked_text = (
            i18n.get("admin_yes", admin_lang)
            if info.is_blocked
            else i18n.get("admin_no", admin_lang)
        )
        lines.append(f"{i18n.get('admin_user_blocked', admin_lang)}: {blocked_text}")
        lines.append(
            f"{i18n.get('admin_user_block_count', admin_lang)}: {info.block_count}"
        )
        if info.blocked_until:
            admin_timezone = get_config().timezone
            localized = info.blocked_until.astimezone(admin_timezone)
            lines.append(
                f"{i18n.get('admin_user_blocked_until', admin_lang)}: "
                f"{localized.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Error in admin_user_info_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_user_info", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_cleanup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        await get_admin_service().cleanup_spam()
        await update.message.reply_text(
            f"✅ {i18n.get('admin_cleanup_success', admin_lang)}"
        )
    except Exception as e:
        logger.exception(f"Error in admin_cleanup_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_cleanup", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_backup_now_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        await get_admin_service().run_manual_backup()
        await update.message.reply_text(i18n.get("admin_backup_success", admin_lang))
    except Exception as e:
        logger.exception(f"Error in admin_backup_now_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_backup_error", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_subscriptions_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        result = await get_admin_service().list_subscriptions()
        if not result.total:
            await update.message.reply_text(
                i18n.get("admin_subscriptions_empty", admin_lang)
            )
            return

        limit = 10
        lines = [
            i18n.get("admin_subscriptions_summary", admin_lang, total=result.total)
        ]
        for index, entry in enumerate(result.items[:limit], start=1):
            time_repr = f"{entry.hour:02d}:{entry.minute:02d}"
            if entry.label and entry.timezone:
                key = "admin_subscriptions_entry_label_tz"
            elif entry.label:
                key = "admin_subscriptions_entry_label"
            elif entry.timezone:
                key = "admin_subscriptions_entry_tz"
            else:
                key = "admin_subscriptions_entry_simple"
            lines.append(
                i18n.get(
                    key,
                    admin_lang,
                    index=index,
                    chat_id=entry.chat_id,
                    time=time_repr,
                    label=entry.label or "",
                    timezone=entry.timezone or "",
                )
            )
        if result.total > limit:
            remaining = result.total - limit
            lines.append(
                i18n.get("admin_subscriptions_more", admin_lang, remaining=remaining)
            )
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.exception(f"Error in admin_subscriptions_cmd: {e}")
        await update.message.reply_text(
            i18n.get("admin_subscriptions_error", admin_lang)
        )


@admin_only(get_config().admin_ids)
async def admin_config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        snapshot = await get_admin_service().get_runtime_config()
        backup_state = (
            i18n.get("admin_config_backup_enabled", admin_lang)
            if snapshot.backup_enabled
            else i18n.get("admin_config_backup_disabled", admin_lang)
        )
        spam_minute, spam_hour, spam_day = snapshot.spam_limits
        message = i18n.get(
            "admin_config_message",
            admin_lang,
            timezone=snapshot.timezone,
            storage=snapshot.storage_path,
            backup_state=backup_state,
            backup_hour=snapshot.backup_hour,
            retention=snapshot.backup_retention_days,
            spam_minute=spam_minute,
            spam_hour=spam_hour,
            spam_day=spam_day,
        )
        await update.message.reply_text(message, parse_mode="HTML")
    except Exception as e:
        logger.exception(f"Error in admin_config_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_config_error", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_test_weather_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from weatherbot.core.exceptions import (
        GeocodeServiceError,
        ValidationError,
        WeatherServiceError,
    )
    from weatherbot.presentation.formatter import format_weather
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    args = context.args or []

    if not args:
        await update.message.reply_text(
            i18n.get("admin_test_weather_usage", admin_lang)
        )
        return

    city = " ".join(args).strip()
    try:
        result = await get_admin_service().test_weather(city)
        prefix = i18n.get(
            "admin_test_weather_prefix", admin_lang, city=result.place_label
        )
        formatted = format_weather(
            result.weather_data, place_label=result.place_label, lang=admin_lang
        )
        await update.message.reply_text(f"{prefix}\n\n{formatted}", parse_mode="HTML")
    except (ValidationError, GeocodeServiceError) as e:
        logger.warning(f"Validation/geocode error in admin_test_weather_cmd: {e}")
        await update.message.reply_text(
            i18n.get("admin_test_weather_not_found", admin_lang, city=city)
        )
    except WeatherServiceError as e:
        logger.exception(f"Weather service error in admin_test_weather_cmd: {e}")
        await update.message.reply_text(
            i18n.get("admin_test_weather_error", admin_lang)
        )
    except Exception as e:
        logger.exception(f"Unexpected error in admin_test_weather_cmd: {e}")
        await update.message.reply_text(
            i18n.get("admin_test_weather_error", admin_lang)
        )


@admin_only(get_config().admin_ids)
async def admin_quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_config = get_config()
    admin_lang = admin_config.admin_language
    try:
        status = await get_admin_service().get_quota_status()

        reset_text = (
            format_reset_time(
                status.reset_at, getattr(admin_config.timezone, "key", None)
            )
            if status.reset_at
            else i18n.get("admin_quota_no_reset", admin_lang)
        )
        percent = min(int(status.ratio * 100), 100)
        message = i18n.get(
            "admin_quota_status_message",
            admin_lang,
            used=status.used,
            limit=status.limit,
            remaining=status.remaining,
            percent=percent,
            reset_time=reset_text,
        )
        await update.message.reply_text(message, parse_mode="HTML")
    except Exception as e:
        logger.exception(f"Error in admin_quota_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_quota_error", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    help_text = f"""
🔧 <b>{i18n.get('admin_commands_title', admin_lang)}:</b>

/admin_stats - {i18n.get('admin_stats_desc', admin_lang)}
/admin_user_info &lt;user_id&gt; - {i18n.get('admin_user_info_desc', admin_lang)}
/admin_unblock &lt;user_id&gt; - {i18n.get('admin_unblock_desc', admin_lang)}
/admin_cleanup - {i18n.get('admin_cleanup_desc', admin_lang)}
/admin_subscriptions - {i18n.get('admin_subscriptions_desc', admin_lang)}
/admin_backup - {i18n.get('admin_backup_desc', admin_lang)}
/admin_config - {i18n.get('admin_config_desc', admin_lang)}
/admin_test_weather &lt;city&gt; - {i18n.get('admin_test_weather_desc', admin_lang)}
/admin_quota - {i18n.get('admin_quota_desc', admin_lang)}
/admin_version - {i18n.get('admin_version_desc', admin_lang)}
/admin_help - {i18n.get('admin_help_desc', admin_lang)}

<b>{i18n.get('admin_examples_title', admin_lang)}:</b>
/admin_user_info 123456789
/admin_unblock 123456789
/admin_test_weather Berlin
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


@admin_only(get_config().admin_ids)
async def admin_version_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        version_info = f"""
🤖 <b>{i18n.get('admin_version_title', admin_lang)}</b>

📦 <b>{i18n.get('admin_version_version', admin_lang)}:</b> {__version__}
📅 <b>{i18n.get('admin_version_date', admin_lang)}:</b> {__release_date__}
🌍 <b>{i18n.get('admin_version_languages', admin_lang)}:</b> {__supported_languages__}
"""
        await update.message.reply_text(version_info, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /admin_version command: {e}")
        await update.message.reply_text(i18n.get("admin_version_error", admin_lang))
