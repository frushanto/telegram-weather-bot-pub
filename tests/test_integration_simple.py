import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.domain.value_objects import UserSubscription
from weatherbot.infrastructure.json_repository import JsonUserRepository


class TestSimpleIntegration:

    async def setup_services(self):

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        temp_file.write("{}")
        temp_file.close()

        repository = JsonUserRepository(temp_file.name)
        user_service = UserService(
            repository, None
        )  # No timezone service for basic tests
        subscription_service = SubscriptionService(repository)
        return {
            "user_service": user_service,
            "subscription_service": subscription_service,
            "user_repository": repository,
            "temp_file": temp_file.name,
        }

    @pytest.mark.asyncio
    async def test_user_language_flow(self):

        services = await self.setup_services()
        user_service = services["user_service"]
        user_id = "123456"

        lang = await user_service.get_user_language(user_id)
        assert lang == "ru"

        await user_service.set_user_language(user_id, "en")
        lang = await user_service.get_user_language(user_id)
        assert lang == "en"

        os.unlink(services["temp_file"])

    @pytest.mark.asyncio
    async def test_subscription_flow(self):

        services = await self.setup_services()
        subscription_service = services["subscription_service"]
        user_repo = services["user_repository"]
        user_id = "789012"

        # First set home location before creating subscription
        user_data = {"lat": 55.7558, "lon": 37.6176, "label": "Moscow"}
        await user_repo.save_user_data(user_id, user_data)

        await subscription_service.set_subscription(user_id, 8, 30)
        sub = await subscription_service.get_subscription_info(user_id)
        assert isinstance(sub, UserSubscription)
        assert sub.hour == 8
        assert sub.minute == 30

    @pytest.mark.asyncio
    async def test_multiple_users(self):

        services = await self.setup_services()
        user_service = services["user_service"]
        user1 = "111111"
        user2 = "222222"

        await user_service.set_user_language(user1, "ru")
        await user_service.set_user_language(user2, "en")

        lang1 = await user_service.get_user_language(user1)
        lang2 = await user_service.get_user_language(user2)
        assert lang1 == "ru"
        assert lang2 == "en"

        os.unlink(services["temp_file"])
