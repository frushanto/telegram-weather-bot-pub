import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAdminCommandsCorrect:

    @pytest.fixture(autouse=True)
    def setup_admin_mock(self, monkeypatch):

        def mock_admin_only_factory(admin_ids):

            def decorator(func):
                return func

            return decorator

        monkeypatch.setattr(
            "weatherbot.core.decorators.admin_only", mock_admin_only_factory
        )

        modules_to_remove = [
            "weatherbot.handlers.admin_commands",
        ]
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                del sys.modules[module_name]

    @pytest.mark.asyncio
    async def test_admin_stats_functionality(self):

        from weatherbot.handlers.admin_commands import admin_stats_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        test_activities = {
            "user_1": MagicMock(daily_requests=10),
            "user_2": MagicMock(daily_requests=50),
            "user_3": MagicMock(daily_requests=200),
        }
        test_blocked = {"user_3"}
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = test_activities
            mock_spam.blocked_users = test_blocked
            await admin_stats_cmd(update, context)

        update.message.reply_text.assert_awaited_once()
        message = update.message.reply_text.await_args[0][0]

        assert "📊" in message
        assert "Всего пользователей: 3" in message
        assert "Заблокированных: 1" in message
        assert "user_3: 200 запросов 🚫" in message
        assert "user_2: 50 запросов" in message

        lines = message.split("\n")
        user_lines = [line for line in lines if "user_" in line and "запросов" in line]
        assert len(user_lines) >= 2

        first_line = user_lines[0]
        assert "user_3" in first_line or "200 запросов" in first_line

    @pytest.mark.asyncio
    async def test_admin_unblock_functionality(self):

        from weatherbot.handlers.admin_commands import admin_unblock_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["123456789"]
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.unblock_user = AsyncMock(return_value=True)
            await admin_unblock_cmd(update, context)

        mock_spam.unblock_user.assert_awaited_once_with(123456789)

        update.message.reply_text.assert_awaited_once()
        success_msg = update.message.reply_text.await_args[0][0]
        assert "123456789" in success_msg
        assert "разблокирован" in success_msg or "unblocked" in success_msg

    @pytest.mark.asyncio
    async def test_admin_cleanup_functionality(self):

        from weatherbot.handlers.admin_commands import admin_cleanup_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.cleanup_old_data = AsyncMock()
            await admin_cleanup_cmd(update, context)

        mock_spam.cleanup_old_data.assert_awaited_once()

        update.message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_stats_empty_data(self):

        from weatherbot.handlers.admin_commands import admin_stats_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = {}
            mock_spam.blocked_users = set()
            await admin_stats_cmd(update, context)
        update.message.reply_text.assert_awaited_once()
        message = update.message.reply_text.await_args[0][0]
        assert "Всего пользователей: 0" in message
        assert "Заблокированных: 0" in message

    @pytest.mark.asyncio
    async def test_admin_unblock_no_args(self):

        from weatherbot.handlers.admin_commands import admin_unblock_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = []
        await admin_unblock_cmd(update, context)

        update.message.reply_text.assert_awaited_once()
        error_msg = update.message.reply_text.await_args[0][0]
        assert "Использование:" in error_msg and "admin_unblock" in error_msg


class TestAdminCommandsRealistic:

    @pytest.fixture(autouse=True)
    def setup_admin_mock(self, monkeypatch):

        def mock_admin_only_factory(admin_ids):
            def decorator(func):
                return func

            return decorator

        monkeypatch.setattr(
            "weatherbot.core.decorators.admin_only", mock_admin_only_factory
        )

        if "weatherbot.handlers.admin_commands" in sys.modules:
            del sys.modules["weatherbot.handlers.admin_commands"]

    @pytest.mark.asyncio
    async def test_realistic_admin_session(self):

        from weatherbot.handlers.admin_commands import (
            admin_stats_cmd,
            admin_unblock_cmd,
        )

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        suspicious_activities = {
            "normal_user_001": MagicMock(daily_requests=8),
            "normal_user_002": MagicMock(daily_requests=12),
            "power_user_003": MagicMock(daily_requests=45),
            "suspicious_004": MagicMock(daily_requests=150),
            "bot_like_005": MagicMock(daily_requests=300),
        }
        blocked = {"suspicious_004", "bot_like_005"}

        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = suspicious_activities
            mock_spam.blocked_users = blocked
            await admin_stats_cmd(update, context)
        stats_message = update.message.reply_text.await_args[0][0]

        assert "Всего пользователей: 5" in stats_message
        assert "Заблокированных: 2" in stats_message
        assert "bot_like_005: 300 запросов 🚫" in stats_message
        assert "suspicious_004: 150 запросов 🚫" in stats_message

        update.message.reply_text.reset_mock()
        context.args = ["123456789"]
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.unblock_user = AsyncMock(return_value=True)
            await admin_unblock_cmd(update, context)

        mock_spam.unblock_user.assert_awaited_once_with(123456789)
        unblock_message = update.message.reply_text.await_args[0][0]
        assert "123456789" in unblock_message

    @pytest.mark.asyncio
    async def test_admin_handles_large_dataset(self):

        from weatherbot.handlers.admin_commands import admin_stats_cmd

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        large_activities = {}
        blocked_users = set()

        for i in range(1000):
            user_id = f"user_{i:04d}"

            if i < 800:
                requests = 1 + (i % 15)
            elif i < 950:
                requests = 20 + (i % 30)
            elif i < 990:
                requests = 50 + (i % 100)
            else:
                requests = 200 + (i % 200)
                blocked_users.add(user_id)
            large_activities[user_id] = MagicMock(daily_requests=requests)
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = large_activities
            mock_spam.blocked_users = blocked_users
            await admin_stats_cmd(update, context)

        stats_message = update.message.reply_text.await_args[0][0]
        assert "Всего пользователей: 1000" in stats_message
        assert "Заблокированных: 10" in stats_message

        assert len(stats_message) > 0

        lines = stats_message.split("\n")

        top_users = [
            line for line in lines if ("ID user_" in line and "запросов" in line)
        ]
        assert len(top_users) >= 5

    @pytest.mark.asyncio
    async def test_admin_commands_error_resilience(self):

        from weatherbot.handlers.admin_commands import (
            admin_stats_cmd,
            admin_unblock_cmd,
        )

        update = MagicMock()
        context = MagicMock()

        update.message.reply_text = AsyncMock(
            side_effect=Exception("Telegram API error")
        )
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = {"test": MagicMock(daily_requests=10)}
            mock_spam.blocked_users = set()

            try:
                await admin_stats_cmd(update, context)
            except Exception:
                pass

        update.message.reply_text = AsyncMock()
        context.args = ["test_user"]
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.unblock_user = AsyncMock(side_effect=Exception("Database error"))
            await admin_unblock_cmd(update, context)

        assert update.message.reply_text.await_count >= 1


class TestAdminCommandsIntegration:

    @pytest.fixture(autouse=True)
    def setup_mock(self, monkeypatch):
        def mock_admin_only_factory(admin_ids):
            def decorator(func):
                return func

            return decorator

        monkeypatch.setattr(
            "weatherbot.core.decorators.admin_only", mock_admin_only_factory
        )
        if "weatherbot.handlers.admin_commands" in sys.modules:
            del sys.modules["weatherbot.handlers.admin_commands"]

    @pytest.mark.asyncio
    async def test_complete_admin_workflow(self):

        from weatherbot.handlers.admin_commands import (
            admin_cleanup_cmd,
            admin_stats_cmd,
            admin_unblock_cmd,
        )

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        test_data = {
            "regular_user": MagicMock(daily_requests=15),
            "blocked_user": MagicMock(daily_requests=180),
        }
        blocked_set = {"blocked_user"}

        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.user_activities = test_data
            mock_spam.blocked_users = blocked_set
            await admin_stats_cmd(update, context)

        stats_msg = update.message.reply_text.await_args[0][0]
        assert "blocked_user: 180 запросов 🚫" in stats_msg

        update.message.reply_text.reset_mock()
        context.args = ["987654321"]
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.unblock_user = AsyncMock(return_value=True)
            await admin_unblock_cmd(update, context)
        mock_spam.unblock_user.assert_awaited_once_with(987654321)

        update.message.reply_text.reset_mock()
        with patch("weatherbot.handlers.admin_commands.spam_protection") as mock_spam:
            mock_spam.cleanup_old_data = AsyncMock()
            await admin_cleanup_cmd(update, context)
        mock_spam.cleanup_old_data.assert_awaited_once()

        assert update.message.reply_text.await_count >= 1
