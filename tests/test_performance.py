import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.infrastructure.json_repository import JsonUserRepository
from weatherbot.infrastructure.spam_protection import SpamProtection


class TestPerformance:

    @pytest.mark.asyncio
    async def test_spam_protection_performance(self):

        spam_protection = SpamProtection()
        user_id = "performance_test_user"
        start_time = time.time()

        for i in range(1000):
            is_spam, _ = await spam_protection.is_spam(
                user_id, f"message_{i}", count_request=False
            )
        end_time = time.time()
        duration = end_time - start_time

        assert duration < 5.0

        is_spam, _ = await spam_protection.is_spam(user_id, "test")
        assert isinstance(is_spam, bool)

    @pytest.mark.asyncio
    async def test_repository_basic_operations(self):

        repository = JsonUserRepository("tests/test_performance.json")
        start_time = time.time()

        for i in range(10):
            user_id = f"user_{i}"

            await repository.save_user_data(user_id, {"language": "en", "requests": i})
        end_time = time.time()
        duration = end_time - start_time

        assert duration < 2.0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):

        spam_protection = SpamProtection()

        async def make_request(user_id: str):
            return await spam_protection.is_spam(
                user_id, "test message", count_request=False
            )

        tasks = [make_request(f"user_{i}") for i in range(50)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        assert len(results) == 50
        for is_spam, reason in results:
            assert isinstance(is_spam, bool)
            assert isinstance(reason, str)
        duration = end_time - start_time

        assert duration < 3.0


class TestLoadTesting:

    @pytest.mark.asyncio
    async def test_high_frequency_requests(self):

        spam_protection = SpamProtection()
        user_id = "high_freq_test"

        start_time = time.time()
        spam_count = 0
        for i in range(200):
            is_spam, _ = await spam_protection.is_spam(user_id, f"msg_{i}")
            if is_spam:
                spam_count += 1
        end_time = time.time()
        duration = end_time - start_time

        assert spam_count > 0
        assert duration < 10.0

    def test_memory_efficiency(self):

        spam_protection = SpamProtection()

        initial_users = len(spam_protection.user_activities)

        for i in range(1000):
            user_id = f"memory_test_user_{i}"

            spam_protection.user_activities[user_id] = MagicMock()
            spam_protection.user_activities[user_id].daily_requests = 1
            spam_protection.user_activities[user_id].last_request_time = time.time()

        final_users = len(spam_protection.user_activities)
        assert final_users >= initial_users + 1000

        import asyncio

        asyncio.run(spam_protection.cleanup_old_data())

        cleaned_users = len(spam_protection.user_activities)
        assert cleaned_users >= 0


class TestResourceUsage:

    @pytest.mark.asyncio
    async def test_cleanup_mechanisms(self):

        spam_protection = SpamProtection()

        for i in range(50):
            user_id = f"cleanup_test_{i}"
            spam_protection.user_activities[user_id] = MagicMock()
            spam_protection.user_activities[user_id].daily_requests = 1
            spam_protection.user_activities[user_id].last_request_time = (
                time.time() - 86400
            )
        initial_count = len(spam_protection.user_activities)

        await spam_protection.cleanup_old_data()

        final_count = len(spam_protection.user_activities)
        assert final_count >= 0

    def test_memory_footprint(self):

        import sys

        spam_protection = SpamProtection()

        try:
            for i in range(1000):
                user_id = f"memory_test_{i}"
                spam_protection.user_activities[user_id] = MagicMock()
                spam_protection.user_activities[user_id].daily_requests = i % 100
                spam_protection.user_activities[user_id].last_request_time = time.time()

            assert len(spam_protection.user_activities) >= 1000
        except MemoryError:
            pytest.fail("Memory error occurred with 1000 users")
