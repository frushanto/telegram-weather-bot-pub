from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.core.decorators import admin_only, spam_check


class TestDecorators:

    def test_admin_only_decorator_allows_admin(self):

        @admin_only([12345])
        async def test_function(update, context):
            return "success"

        update = MagicMock()
        update.effective_user.id = 12345
        context = MagicMock()

    def test_admin_only_decorator_blocks_non_admin(self):

        @admin_only([12345])
        async def test_function(update, context):
            return "success"

        update = MagicMock()
        update.effective_user.id = 99999
        update.message.reply_text = MagicMock()
        context = MagicMock()

    @pytest.mark.asyncio
    async def test_spam_check_allows_normal_user(self):

        @spam_check
        async def test_function(update, context):
            return "success"

        update = MagicMock()
        update.effective_chat.id = 123456
        context = MagicMock()
        with patch("weatherbot.core.decorators.spam_protection") as mock_spam:

            async def mock_is_spam(*args, **kwargs):
                return (False, "")

            mock_spam.is_spam = mock_is_spam
            result = await test_function(update, context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_spam_check_blocks_spam(self):

        @spam_check
        async def test_function(update, context):
            return "success"

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("weatherbot.core.decorators.spam_protection") as mock_spam:

            async def mock_is_spam(*args, **kwargs):
                return (True, "Too many requests")

            mock_spam.is_spam = mock_is_spam
            result = await test_function(update, context)

        assert result is None


class TestSpamProtectionIntegration:

    @pytest.mark.asyncio
    async def test_spam_protection_integration(self):

        from weatherbot.infrastructure.spam_protection import SpamProtection

        spam_protection = SpamProtection()
        user_id = "test_user"

        is_spam, reason = await spam_protection.is_spam(user_id, "normal message")
        assert not is_spam

        is_spam, reason = await spam_protection.is_spam(user_id, "another message")

        assert user_id in spam_protection.user_activities

    @pytest.mark.asyncio
    async def test_spam_protection_with_long_messages(self):

        from weatherbot.infrastructure.spam_protection import SpamProtection

        spam_protection = SpamProtection()
        user_id = "test_user_long"

        long_message = "A" * 2000
        is_spam, reason = await spam_protection.is_spam(user_id, long_message)

        if is_spam:
            assert "длин" in reason.lower() or "long" in reason.lower()

    def test_spam_config_loading(self):

        from weatherbot.infrastructure.spam_protection import get_spam_config

        config = get_spam_config()

        assert hasattr(config, "max_requests_per_minute")
        assert hasattr(config, "max_requests_per_hour")
        assert hasattr(config, "max_requests_per_day")
        assert hasattr(config, "block_duration")

        assert config.max_requests_per_minute > 0
        assert config.max_requests_per_hour > 0
        assert config.max_requests_per_day > 0
