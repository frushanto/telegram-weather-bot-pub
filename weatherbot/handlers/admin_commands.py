import logging

from telegram import Update
from telegram.ext import ContextTypes

from weatherbot import __release_date__, __supported_languages__, __version__
from weatherbot.core.config import get_config
from weatherbot.core.decorators import admin_only
from weatherbot.infrastructure.spam_protection import spam_protection

logger = logging.getLogger(__name__)


@admin_only(get_config().admin_ids)
async def admin_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    from weatherbot.core.config import get_config
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        stats = []
        user_count = len(spam_protection.user_activities)
        blocked_count = len(spam_protection.blocked_users)
        stats.append(f"📊 **{i18n.get('admin_stats_title', admin_lang)}**")
        stats.append(f"{i18n.get('admin_total_users', admin_lang)}: {user_count}")
        stats.append(f"{i18n.get('admin_blocked_users', admin_lang)}: {blocked_count}")
        stats.append("")

        if spam_protection.user_activities:
            sorted_users = sorted(
                spam_protection.user_activities.items(),
                key=lambda x: x[1].daily_requests,
                reverse=True,
            )[:10]
            stats.append(f"🔥 **{i18n.get('admin_top_users', admin_lang)}:**")
            for i, (user_id, activity) in enumerate(sorted_users, 1):
                blocked_status = (
                    " 🚫" if user_id in spam_protection.blocked_users else ""
                )
                stats.append(
                    f"{i}. ID {user_id}: {activity.daily_requests} {i18n.get('admin_requests_today', admin_lang)}{blocked_status}"
                )
        message = "\n".join(stats)
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Error in admin_stats_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_stats", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    from weatherbot.core.config import get_config
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
        success = await spam_protection.unblock_user(user_id)
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

    from weatherbot.core.config import get_config
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
        stats = spam_protection.get_user_stats(user_id)
        info = []
        info.append(
            f"👤 **{i18n.get('admin_user_info_title', admin_lang, user_id=user_id)}:**"
        )
        info.append(
            f"{i18n.get('admin_user_requests_today', admin_lang)}: {stats['requests_today']}"
        )
        blocked_text = (
            i18n.get("admin_yes", admin_lang)
            if stats["is_blocked"]
            else i18n.get("admin_no", admin_lang)
        )
        info.append(f"{i18n.get('admin_user_blocked', admin_lang)}: {blocked_text}")
        info.append(
            f"{i18n.get('admin_user_block_count', admin_lang)}: {stats['block_count']}"
        )
        if stats["blocked_until"]:
            from datetime import datetime

            blocked_until = datetime.fromtimestamp(stats["blocked_until"])
            info.append(
                f"{i18n.get('admin_user_blocked_until', admin_lang)}: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        message = "\n".join(info)
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Error in admin_user_info_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_user_info", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_cleanup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    from weatherbot.core.config import get_config
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    try:
        await spam_protection.cleanup_old_data()
        await update.message.reply_text(
            f"✅ {i18n.get('admin_cleanup_success', admin_lang)}"
        )
    except Exception as e:
        logger.exception(f"Error in admin_cleanup_cmd: {e}")
        await update.message.reply_text(i18n.get("admin_error_cleanup", admin_lang))


@admin_only(get_config().admin_ids)
async def admin_help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    from weatherbot.core.config import get_config
    from weatherbot.presentation.i18n import i18n

    admin_lang = get_config().admin_language
    help_text = f"""
🔧 <b>{i18n.get('admin_commands_title', admin_lang)}:</b>

/admin_stats - {i18n.get('admin_stats_desc', admin_lang)}
/admin_user_info &lt;user_id&gt; - {i18n.get('admin_user_info_desc', admin_lang)}
/admin_unblock &lt;user_id&gt; - {i18n.get('admin_unblock_desc', admin_lang)}
/admin_cleanup - {i18n.get('admin_cleanup_desc', admin_lang)}
/admin_version - {i18n.get('admin_version_desc', admin_lang)}
/admin_help - {i18n.get('admin_help_desc', admin_lang)}

<b>{i18n.get('admin_examples_title', admin_lang)}:</b>
/admin_user_info 123456789
/admin_unblock 123456789
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


@admin_only(get_config().admin_ids)
async def admin_version_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    from weatherbot.core.config import get_config
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
