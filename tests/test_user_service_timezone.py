from unittest.mock import AsyncMock, MagicMock

import pytest

from weatherbot.application.user_service import UserService
from weatherbot.core.exceptions import StorageError, ValidationError
from weatherbot.infrastructure.timezone_service import TimezoneService


class TestUserServiceTimezone:

    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_timezone_service(self):
        service = MagicMock(spec=TimezoneService)
        service.get_timezone_by_coordinates.return_value = "Europe/Moscow"
        return service

    @pytest.fixture
    def user_service(self, mock_user_repo, mock_timezone_service):
        return UserService(mock_user_repo, mock_timezone_service)

    @pytest.mark.asyncio
    async def test_set_user_home_with_timezone(
        self, user_service, mock_user_repo, mock_timezone_service
    ):
        """Test that timezone is automatically set when setting home location"""
        mock_user_repo.get_user_data.return_value = {}
        mock_timezone_service.get_timezone_by_coordinates.return_value = "Europe/Moscow"

        await user_service.set_user_home("123", 55.7558, 37.6176, "Moscow")

        # Verify timezone service was called with coordinates
        mock_timezone_service.get_timezone_by_coordinates.assert_called_once_with(
            55.7558, 37.6176
        )

        # Verify user data was saved with timezone
        mock_user_repo.save_user_data.assert_called_once()
        args, kwargs = mock_user_repo.save_user_data.call_args
        user_data = args[1]
        assert user_data["timezone"] == "Europe/Moscow"
        assert user_data["lat"] == 55.7558
        assert user_data["lon"] == 37.6176
        assert user_data["label"] == "Moscow"

    @pytest.mark.asyncio
    async def test_set_user_home_timezone_not_found(
        self, user_service, mock_user_repo, mock_timezone_service
    ):
        """Test behavior when timezone cannot be determined"""
        mock_user_repo.get_user_data.return_value = {}
        mock_timezone_service.get_timezone_by_coordinates.return_value = None

        await user_service.set_user_home("123", 0.0, 0.0, "Ocean")

        # Verify user data was saved without timezone
        mock_user_repo.save_user_data.assert_called_once()
        args, kwargs = mock_user_repo.save_user_data.call_args
        user_data = args[1]
        assert "timezone" not in user_data
        assert user_data["lat"] == 0.0
        assert user_data["lon"] == 0.0
        assert user_data["label"] == "Ocean"

    @pytest.mark.asyncio
    async def test_set_user_home_without_timezone_service(self, mock_user_repo):
        """Test that setting home works without timezone service"""
        user_service = UserService(mock_user_repo, None)
        mock_user_repo.get_user_data.return_value = {}

        await user_service.set_user_home("123", 55.7558, 37.6176, "Moscow")

        # Verify user data was saved without timezone
        mock_user_repo.save_user_data.assert_called_once()
        args, kwargs = mock_user_repo.save_user_data.call_args
        user_data = args[1]
        assert "timezone" not in user_data

    @pytest.mark.asyncio
    async def test_get_user_home_with_timezone(self, user_service, mock_user_repo):
        """Test that get_user_home returns timezone if available"""
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "label": "Moscow",
            "timezone": "Europe/Moscow",
        }

        home = await user_service.get_user_home("123")

        assert home is not None
        assert home.timezone == "Europe/Moscow"
        assert home.lat == 55.7558
        assert home.lon == 37.6176
        assert home.label == "Moscow"

    @pytest.mark.asyncio
    async def test_get_user_home_without_timezone(self, user_service, mock_user_repo):
        """Test that get_user_home works without timezone"""
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "label": "Moscow",
        }

        home = await user_service.get_user_home("123")

        assert home is not None
        assert home.timezone is None
        assert home.lat == 55.7558
        assert home.lon == 37.6176
        assert home.label == "Moscow"

    @pytest.mark.asyncio
    async def test_remove_user_home_removes_timezone(
        self, user_service, mock_user_repo
    ):
        """Test that removing home also removes timezone"""
        mock_user_repo.get_user_data.return_value = {
            "lat": 55.7558,
            "lon": 37.6176,
            "label": "Moscow",
            "timezone": "Europe/Moscow",
            "language": "ru",
        }

        removed = await user_service.remove_user_home("123")

        assert removed is True
        if mock_user_repo.save_user_data.await_count:
            args, kwargs = mock_user_repo.save_user_data.call_args
            remaining_data = args[1]

            assert "timezone" not in remaining_data
            assert "lat" not in remaining_data
            assert "lon" not in remaining_data
            assert "label" not in remaining_data
            assert remaining_data["language"] == "ru"
        else:
            mock_user_repo.delete_user_data.assert_awaited_once_with("123")

    @pytest.mark.asyncio
    async def test_get_user_profile_returns_value_object(
        self, user_service, mock_user_repo
    ):
        mock_user_repo.get_user_data.return_value = {
            "lat": 10.0,
            "lon": 20.0,
            "label": "Test",
            "timezone": "UTC",
            "sub_hour": 6,
            "sub_min": 15,
            "language": "en",
        }

        profile = await user_service.get_user_profile("abc")

        assert profile.language == "en"
        assert profile.home and profile.home.label == "Test"
        assert profile.home.timezone == "UTC"
        assert profile.subscription and profile.subscription.hour == 6
