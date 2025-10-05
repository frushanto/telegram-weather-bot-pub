from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from weatherbot.core.decorators import spam_check
from weatherbot.infrastructure.spam_protection import SpamProtection


@pytest.mark.asyncio
async def test_blocked_user_spam_notification_throttling():

    spam_protection = SpamProtection()

    handler_called = []

    @spam_check
    async def test_handler(update, context):
        handler_called.append(True)
        return "Handler executed"

    with patch(
        "weatherbot.core.decorators._get_spam_service",
        return_value=spam_protection,
    ):

        long_message = "x" * 1001
        update1 = MagicMock()
        update1.effective_user.id = 123456
        update1.message.text = long_message
        update1.message.reply_text = AsyncMock()
        update1.callback_query = None
        context = MagicMock()

        result = await test_handler(update1, context)
        assert result is None
        assert len(handler_called) == 0

        update1.message.reply_text.assert_called_once()
        call_args = update1.message.reply_text.call_args[0][0]
        assert "⚠️" in call_args
        assert "Сообщение слишком длинное" in call_args

        update2 = MagicMock()
        update2.effective_user.id = 123456
        update2.message.text = "Другое сообщение"
        update2.message.reply_text = AsyncMock()
        update2.callback_query = None

        result = await test_handler(update2, context)
        assert result is None
        assert len(handler_called) == 0

        update2.message.reply_text.assert_called_once()

        update3 = MagicMock()
        update3.effective_user.id = 123456
        update3.message.text = "Еще одно сообщение"
        update3.message.reply_text = AsyncMock()
        update3.callback_query = None

        result = await test_handler(update3, context)
        assert result is None
        assert len(handler_called) == 0

        update3.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_unblocked_user_gets_notification_again():

    spam_protection = SpamProtection()
    handler_called = []

    @spam_check
    async def test_handler(update, context):
        handler_called.append(True)
        return "Handler executed"

    with patch(
        "weatherbot.core.decorators._get_spam_service",
        return_value=spam_protection,
    ):

        await spam_protection._block_user(123456, "Test block")

        update1 = MagicMock()
        update1.effective_user.id = 123456
        update1.message.text = "test message"
        update1.message.reply_text = AsyncMock()
        update1.callback_query = None
        context = MagicMock()
        await test_handler(update1, context)
        update1.message.reply_text.assert_called_once()

        await spam_protection.unblock_user(123456)

        await spam_protection._block_user(123456, "New test block")

        update2 = MagicMock()
        update2.effective_user.id = 123456
        update2.message.text = "new test message"
        update2.message.reply_text = AsyncMock()
        update2.callback_query = None
        await test_handler(update2, context)
        update2.message.reply_text.assert_called_once()
