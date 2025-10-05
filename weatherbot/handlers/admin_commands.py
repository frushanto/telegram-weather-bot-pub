from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot import __release_date__, __supported_languages__, __version__
from weatherbot.application.interfaces import AdminApplicationServiceProtocol
from weatherbot.core.config import BotConfig
from weatherbot.core.decorators import admin_only
from weatherbot.handlers.command_types import CommandArgs, normalize_command_args
from weatherbot.presentation.i18n import Localization
from weatherbot.utils.time import format_reset_time

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AdminHandlerDependencies:
    admin_service: AdminApplicationServiceProtocol
    localization: Localization
    config_provider: Callable[[], BotConfig]


_deps: AdminHandlerDependencies | None = None
_BASE_HANDLERS: dict[str, Callable] = {}


def configure_admin_handlers(deps: AdminHandlerDependencies) -> None:
    global _deps
    _deps = deps

    admin_ids = set(deps.config_provider().admin_ids or [])
    decorator = admin_only(admin_ids)

    for name, func in _BASE_HANDLERS.items():
        globals()[name] = decorator(func)


def _require_deps() -> AdminHandlerDependencies:
    if _deps is None:
        raise RuntimeError("Admin handler dependencies are not configured")
    return _deps


def _localization():
    return _require_deps().localization


def _config():
    return _require_deps().config_provider()


def _service():
    return _require_deps().admin_service


async def _admin_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        stats = await _service().get_stats()
        lines = [
            f"📊 **{localization.get('admin_stats_title', admin_lang)}**",
            f"{localization.get('admin_total_users', admin_lang)}: {stats.user_count}",
            f"{localization.get('admin_blocked_users', admin_lang)}: {stats.blocked_count}",
            "",
        ]
        if stats.top_users:
            lines.append(f"🔥 **{localization.get('admin_top_users', admin_lang)}:**")
            for index, top_user in enumerate(stats.top_users, start=1):
                blocked_suffix = " 🚫" if top_user.is_blocked else ""
                lines.append(
                    f"{index}. ID {top_user.user_id}: {top_user.daily_requests} "
                    f"{localization.get('admin_requests_today', admin_lang)}{blocked_suffix}"
                )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_stats_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_error_stats", admin_lang)
        )


async def _admin_unblock_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        args: CommandArgs = normalize_command_args(context.args)
        if not args:
            await update.message.reply_text(
                localization.get("admin_unblock_usage", admin_lang)
            )
            return
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                localization.get("admin_invalid_user_id", admin_lang)
            )
            return
        success = await _service().unblock_user(user_id)
        if success:
            await update.message.reply_text(
                f"✅ {localization.get('admin_user_unblocked', admin_lang, user_id=user_id)}"
            )
        else:
            await update.message.reply_text(
                f"❌ {localization.get('admin_user_not_found', admin_lang, user_id=user_id)}"
            )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_unblock_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_error_unblock", admin_lang)
        )


async def _admin_user_info_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    config = _config()
    admin_lang = config.admin_language
    try:
        args: CommandArgs = normalize_command_args(context.args)
        if not args:
            await update.message.reply_text(
                localization.get("admin_user_info_usage", admin_lang)
            )
            return
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                localization.get("admin_invalid_user_id", admin_lang)
            )
            return

        info = await _service().get_user_info(user_id)
        lines = [
            f"👤 **{localization.get('admin_user_info_title', admin_lang, user_id=user_id)}:**",
            f"{localization.get('admin_user_requests_today', admin_lang)}: {info.requests_today}",
        ]
        blocked_text = (
            localization.get("admin_yes", admin_lang)
            if info.is_blocked
            else localization.get("admin_no", admin_lang)
        )
        lines.append(
            f"{localization.get('admin_user_blocked', admin_lang)}: {blocked_text}"
        )
        lines.append(
            f"{localization.get('admin_user_block_count', admin_lang)}: {info.block_count}"
        )
        if info.blocked_until:
            admin_timezone = config.timezone
            localized = info.blocked_until.astimezone(admin_timezone)
            lines.append(
                f"{localization.get('admin_user_blocked_until', admin_lang)}: "
                f"{localized.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_user_info_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_error_user_info", admin_lang)
        )


async def _admin_cleanup_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        await _service().cleanup_spam()
        await update.message.reply_text(
            f"✅ {localization.get('admin_cleanup_success', admin_lang)}"
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_cleanup_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_error_cleanup", admin_lang)
        )


async def _admin_backup_now_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        await _service().run_manual_backup()
        await update.message.reply_text(
            localization.get("admin_backup_success", admin_lang)
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_backup_now_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_backup_error", admin_lang)
        )


async def _admin_subscriptions_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        result = await _service().list_subscriptions()
        if not result.total:
            await update.message.reply_text(
                localization.get("admin_subscriptions_empty", admin_lang)
            )
            return

        limit = 10
        lines = [
            localization.get(
                "admin_subscriptions_summary", admin_lang, total=result.total
            )
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
                localization.get(
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
                localization.get(
                    "admin_subscriptions_more", admin_lang, remaining=remaining
                )
            )
        await update.message.reply_text("\n".join(lines))
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_subscriptions_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_subscriptions_error", admin_lang)
        )


async def _admin_config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        snapshot = await _service().get_runtime_config()
        backup_state = (
            localization.get("admin_config_backup_enabled", admin_lang)
            if snapshot.backup_enabled
            else localization.get("admin_config_backup_disabled", admin_lang)
        )
        spam_minute, spam_hour, spam_day = snapshot.spam_limits
        message = localization.get(
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
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_config_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_config_error", admin_lang)
        )


async def _admin_test_weather_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from weatherbot.core.exceptions import (
        GeocodeServiceError,
        ValidationError,
        WeatherServiceError,
    )
    from weatherbot.presentation.formatter import format_weather

    localization = _localization()
    admin_lang = _config().admin_language
    args: CommandArgs = normalize_command_args(context.args)

    if not args:
        await update.message.reply_text(
            localization.get("admin_test_weather_usage", admin_lang)
        )
        return

    city = " ".join(args).strip()
    try:
        result = await _service().test_weather(city)
        prefix = localization.get(
            "admin_test_weather_prefix", admin_lang, city=result.place_label
        )
        formatted = format_weather(
            result.weather_data, place_label=result.place_label, lang=admin_lang
        )
        await update.message.reply_text(f"{prefix}\n\n{formatted}", parse_mode="HTML")
    except (ValidationError, GeocodeServiceError) as e:
        logger.warning("Validation/geocode error in admin_test_weather_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_test_weather_not_found", admin_lang, city=city)
        )
    except WeatherServiceError as e:
        logger.exception("Weather service error in admin_test_weather_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_test_weather_error", admin_lang)
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Unexpected error in admin_test_weather_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_test_weather_error", admin_lang)
        )


async def _admin_quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    localization = _localization()
    config = _config()
    admin_lang = config.admin_language
    try:
        status = await _service().get_quota_status()

        reset_text = (
            format_reset_time(status.reset_at, getattr(config.timezone, "key", None))
            if status.reset_at
            else localization.get("admin_quota_no_reset", admin_lang)
        )
        percent = min(int(status.ratio * 100), 100)
        message = localization.get(
            "admin_quota_status_message",
            admin_lang,
            used=status.used,
            limit=status.limit,
            remaining=status.remaining,
            percent=percent,
            reset_time=reset_text,
        )
        await update.message.reply_text(message, parse_mode="HTML")
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error in admin_quota_cmd: %s", e)
        await update.message.reply_text(
            localization.get("admin_quota_error", admin_lang)
        )


async def _admin_help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    help_text = f"""
🔧 <b>{localization.get('admin_commands_title', admin_lang)}:</b>

/admin_stats - {localization.get('admin_stats_desc', admin_lang)}
/admin_user_info &lt;user_id&gt; - {localization.get('admin_user_info_desc', admin_lang)}
/admin_unblock &lt;user_id&gt; - {localization.get('admin_unblock_desc', admin_lang)}
/admin_cleanup - {localization.get('admin_cleanup_desc', admin_lang)}
/admin_subscriptions - {localization.get('admin_subscriptions_desc', admin_lang)}
/admin_backup - {localization.get('admin_backup_desc', admin_lang)}
/admin_config - {localization.get('admin_config_desc', admin_lang)}
/admin_test_weather &lt;city&gt; - {localization.get('admin_test_weather_desc', admin_lang)}
/admin_quota - {localization.get('admin_quota_desc', admin_lang)}
/admin_version - {localization.get('admin_version_desc', admin_lang)}
/admin_help - {localization.get('admin_help_desc', admin_lang)}

<b>{localization.get('admin_examples_title', admin_lang)}:</b>
/admin_user_info 123456789
/admin_unblock 123456789
/admin_test_weather Berlin
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


async def _admin_version_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    localization = _localization()
    admin_lang = _config().admin_language
    try:
        version_info = f"""
🤖 <b>{localization.get('admin_version_title', admin_lang)}</b>

📦 <b>{localization.get('admin_version_version', admin_lang)}:</b> {__version__}
📅 <b>{localization.get('admin_version_date', admin_lang)}:</b> {__release_date__}
🌍 <b>{localization.get('admin_version_languages', admin_lang)}:</b> {__supported_languages__}
"""
        await update.message.reply_text(version_info, parse_mode="HTML")
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error("Error in /admin_version command: %s", e)
        await update.message.reply_text(
            localization.get("admin_version_error", admin_lang)
        )


admin_stats_cmd = _admin_stats_cmd
admin_unblock_cmd = _admin_unblock_cmd
admin_user_info_cmd = _admin_user_info_cmd
admin_cleanup_cmd = _admin_cleanup_cmd
admin_backup_now_cmd = _admin_backup_now_cmd
admin_subscriptions_cmd = _admin_subscriptions_cmd
admin_config_cmd = _admin_config_cmd
admin_test_weather_cmd = _admin_test_weather_cmd
admin_quota_cmd = _admin_quota_cmd
admin_help_cmd = _admin_help_cmd
admin_version_cmd = _admin_version_cmd

_BASE_HANDLERS.update(
    {
        "admin_stats_cmd": _admin_stats_cmd,
        "admin_unblock_cmd": _admin_unblock_cmd,
        "admin_user_info_cmd": _admin_user_info_cmd,
        "admin_cleanup_cmd": _admin_cleanup_cmd,
        "admin_backup_now_cmd": _admin_backup_now_cmd,
        "admin_subscriptions_cmd": _admin_subscriptions_cmd,
        "admin_config_cmd": _admin_config_cmd,
        "admin_test_weather_cmd": _admin_test_weather_cmd,
        "admin_quota_cmd": _admin_quota_cmd,
        "admin_help_cmd": _admin_help_cmd,
        "admin_version_cmd": _admin_version_cmd,
    }
)
