from unittest.mock import AsyncMock

import pytest

from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.core.exceptions import ValidationError


class TestSubscriptionServiceTimezone:

    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()

    @pytest.fixture
    def subscription_service(self, mock_user_repo):
        return SubscriptionService(mock_user_repo)

    @pytest.mark.asyncio
    async def test_set_subscription_requires_home_location(
        self, subscription_service, mock_user_repo
    ):
        """Test that subscription requires home location to be set"""
        # User with no home location
        mock_user_repo.get_user_data.return_value = {"language": "ru"}

        with pytest.raises(ValidationError, match="Home location must be set"):
            await subscription_service.set_subscription("123", 8, 0)

    @pytest.mark.asyncio
    async def test_set_subscription_with_home_location(
        self, subscription_service, mock_user_repo
    ):
        """Test successful subscription with home location set"""
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "label": "Moscow",
            "timezone": "Europe/Moscow",
            "language": "ru",
        }

        await subscription_service.set_subscription("123", 8, 30)

        # Verify subscription was saved
        mock_user_repo.save_user_data.assert_called_once()
        args, kwargs = mock_user_repo.save_user_data.call_args
        user_data = args[1]

        assert user_data["sub_hour"] == 8
        assert user_data["sub_min"] == 30
        assert user_data["timezone"] == "Europe/Moscow"  # Should preserve timezone

    @pytest.mark.asyncio
    async def test_set_subscription_with_home_no_timezone(
        self, subscription_service, mock_user_repo
    ):
        """Test subscription works even without timezone"""
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "label": "Moscow",
            "language": "ru",
        }

        await subscription_service.set_subscription("123", 8, 30)

        # Should still work
        mock_user_repo.save_user_data.assert_called_once()
        args, kwargs = mock_user_repo.save_user_data.call_args
        user_data = args[1]

        assert user_data["sub_hour"] == 8
        assert user_data["sub_min"] == 30

    @pytest.mark.asyncio
    async def test_set_subscription_partial_home_location(
        self, subscription_service, mock_user_repo
    ):
        """Test subscription fails with incomplete home location"""
        # Missing label
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "language": "ru",
        }

        with pytest.raises(ValidationError, match="Home location must be set"):
            await subscription_service.set_subscription("123", 8, 0)

        # Missing lon
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "label": "Moscow",
            "language": "ru",
        }

        with pytest.raises(ValidationError, match="Home location must be set"):
            await subscription_service.set_subscription("123", 8, 0)

    @pytest.mark.asyncio
    async def test_get_all_subscriptions_includes_timezone(
        self, subscription_service, mock_user_repo
    ):
        """Test that subscription list includes timezone information"""
        mock_user_repo.get_all_users.return_value = {
            "123": {
                "lat": 55.7558,
                "lon": 37.6176,
                "label": "Moscow",
                "timezone": "Europe/Moscow",
                "sub_hour": 8,
                "sub_min": 30,
                "language": "ru",
            },
            "456": {
                "lat": 40.7128,
                "lon": -74.0060,
                "label": "New York",
                "timezone": "America/New_York",
                "sub_hour": 9,
                "sub_min": 0,
                "language": "en",
            },
        }

        subscriptions = await subscription_service.get_all_subscriptions()

        assert len(subscriptions) == 2

        moscow_sub = next(sub for sub in subscriptions if sub["chat_id"] == "123")
        assert moscow_sub["hour"] == 8
        assert moscow_sub["minute"] == 30
        assert moscow_sub["user_data"]["timezone"] == "Europe/Moscow"

        ny_sub = next(sub for sub in subscriptions if sub["chat_id"] == "456")
        assert ny_sub["hour"] == 9
        assert ny_sub["minute"] == 0
        assert ny_sub["user_data"]["timezone"] == "America/New_York"
