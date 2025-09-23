import time
from unittest.mock import AsyncMock, patch

import pytest

from weatherbot.infrastructure.spam_protection import SpamProtection, get_spam_config


@pytest.fixture
def spam_protection():

    return SpamProtection()


@pytest.mark.asyncio
async def test_first_block_notification_sent(spam_protection):

    user_id = 123456

    await spam_protection._block_user(user_id, "Test block")

    is_spam, reason = await spam_protection.is_spam(user_id, "test message")
    assert is_spam
    assert reason != "SILENT_BLOCK"
    assert "заблокированы" in reason


@pytest.mark.asyncio
async def test_subsequent_block_notifications_silent(spam_protection):

    user_id = 123456

    await spam_protection._block_user(user_id, "Test block")

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 1")
    assert is_spam
    assert reason != "SILENT_BLOCK"

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 2")
    assert is_spam
    assert reason == "SILENT_BLOCK"
    is_spam, reason = await spam_protection.is_spam(user_id, "test message 3")
    assert is_spam
    assert reason == "SILENT_BLOCK"


@pytest.mark.asyncio
async def test_notification_after_timeout(spam_protection):

    user_id = 123456

    await spam_protection._block_user(user_id, "Test block")

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 1")
    assert is_spam
    assert reason != "SILENT_BLOCK"

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 2")
    assert is_spam
    assert reason == "SILENT_BLOCK"

    activity = spam_protection.user_activities[user_id]
    activity.last_block_notification = time.time() - 301

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 3")
    assert is_spam
    assert reason != "SILENT_BLOCK"
    assert "заблокированы" in reason


@pytest.mark.asyncio
async def test_new_block_resets_notification(spam_protection):

    user_id = 123456

    long_message = "x" * (get_spam_config().max_message_length + 1)
    is_spam, reason = await spam_protection.is_spam(user_id, long_message)
    assert is_spam
    assert reason != "SILENT_BLOCK"

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 2")
    assert is_spam
    assert reason != "SILENT_BLOCK"

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 3")
    assert is_spam
    assert reason == "SILENT_BLOCK"


@pytest.mark.asyncio
async def test_unblock_resets_notification(spam_protection):

    user_id = 123456

    await spam_protection._block_user(user_id, "Test block")

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 1")
    assert is_spam
    assert reason != "SILENT_BLOCK"

    success = await spam_protection.unblock_user(user_id)
    assert success

    await spam_protection._block_user(user_id, "New block")

    is_spam, reason = await spam_protection.is_spam(user_id, "test message 2")
    assert is_spam
    assert reason != "SILENT_BLOCK"
    assert "заблокированы" in reason


@pytest.mark.asyncio
async def test_different_users_independent_notifications(spam_protection):

    user1 = 123456
    user2 = 789012

    await spam_protection._block_user(user1, "Block user 1")
    await spam_protection._block_user(user2, "Block user 2")

    is_spam1, reason1 = await spam_protection.is_spam(user1, "message from user 1")
    assert is_spam1 and reason1 != "SILENT_BLOCK"
    is_spam2, reason2 = await spam_protection.is_spam(user2, "message from user 2")
    assert is_spam2 and reason2 != "SILENT_BLOCK"

    is_spam1, reason1 = await spam_protection.is_spam(user1, "message 2 from user 1")
    assert is_spam1 and reason1 == "SILENT_BLOCK"
    is_spam2, reason2 = await spam_protection.is_spam(user2, "message 2 from user 2")
    assert is_spam2 and reason2 == "SILENT_BLOCK"
