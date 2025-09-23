import asyncio
import time

import pytest

from weatherbot.infrastructure.spam_protection import SpamProtection, get_spam_config


@pytest.fixture
def spam_protection():

    return SpamProtection()


@pytest.mark.asyncio
async def test_normal_requests_allowed(spam_protection):

    user_id = 123456

    is_spam, reason = await spam_protection.is_spam(user_id, "test message")
    assert not is_spam
    assert reason == ""


@pytest.mark.asyncio
async def test_too_frequent_requests_blocked(spam_protection):

    user_id = 123456

    await spam_protection.is_spam(user_id, "test1")

    is_spam, reason = await spam_protection.is_spam(user_id, "test2")
    assert is_spam
    assert "Слишком быстро" in reason


@pytest.mark.asyncio
async def test_too_many_requests_per_minute(spam_protection):

    user_id = 123456

    await spam_protection.is_spam(user_id, "test0")

    for i in range(1, get_spam_config().max_requests_per_minute):

        spam_protection.user_activities[user_id].last_request_time = time.time() - 2
        await spam_protection.is_spam(user_id, f"test{i}")

    spam_protection.user_activities[user_id].last_request_time = time.time() - 2
    is_spam, reason = await spam_protection.is_spam(user_id, "overflow")
    assert is_spam
    assert "лимит запросов в минуту" in reason


@pytest.mark.asyncio
async def test_long_message_blocked(spam_protection):

    user_id = 123456

    long_message = "x" * (get_spam_config().max_message_length + 1)
    is_spam, reason = await spam_protection.is_spam(user_id, long_message)
    assert is_spam
    assert "длинное" in reason.lower()


@pytest.mark.asyncio
async def test_user_stats(spam_protection):

    user_id = 123456

    await spam_protection.is_spam(user_id, "test")

    stats = spam_protection.get_user_stats(user_id)
    assert stats["requests_today"] == 1
    assert not stats["is_blocked"]
    assert stats["block_count"] == 0


@pytest.mark.asyncio
async def test_user_unblock(spam_protection):

    user_id = 123456

    await spam_protection._block_user(user_id, "test reason")

    stats = spam_protection.get_user_stats(user_id)
    assert stats["is_blocked"]

    success = await spam_protection.unblock_user(user_id)
    assert success

    stats = spam_protection.get_user_stats(user_id)
    assert not stats["is_blocked"]


@pytest.mark.asyncio
async def test_cleanup_old_data(spam_protection):

    user_id = 123456

    await spam_protection.is_spam(user_id, "test")
    assert user_id in spam_protection.user_activities

    old_time = time.time() - (31 * 24 * 3600)
    spam_protection.user_activities[user_id].last_request_time = old_time

    await spam_protection.cleanup_old_data()

    assert user_id not in spam_protection.user_activities


@pytest.mark.asyncio
async def test_different_users_independent(spam_protection):

    user1 = 123456
    user2 = 654321

    await spam_protection.is_spam(user1, "test0")

    for i in range(1, get_spam_config().max_requests_per_minute):
        spam_protection.user_activities[user1].last_request_time = time.time() - 2
        await spam_protection.is_spam(user1, f"test{i}")

    spam_protection.user_activities[user1].last_request_time = time.time() - 2
    is_spam1, _ = await spam_protection.is_spam(user1, "overflow")
    assert is_spam1

    is_spam2, _ = await spam_protection.is_spam(user2, "test")
    assert not is_spam2


@pytest.mark.asyncio
async def test_daily_counter_reset(spam_protection):

    user_id = 123456

    await spam_protection.is_spam(user_id, "test1")

    assert spam_protection.user_activities[user_id].daily_requests == 1

    from datetime import datetime, timedelta

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    spam_protection.user_activities[user_id].last_reset_date = yesterday
    spam_protection.user_activities[user_id].daily_requests = 100

    spam_protection.user_activities[user_id].last_request_time = time.time() - 2

    await spam_protection.is_spam(user_id, "test2")

    assert spam_protection.user_activities[user_id].daily_requests == 1
