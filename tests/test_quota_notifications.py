from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.infrastructure.weather_quota import WeatherQuotaStatus


@pytest.mark.asyncio
async def test_notify_quota_sends_alerts_and_marks(tmp_path):

    status = WeatherQuotaStatus(
        limit=1000,
        used=900,
        remaining=100,
        reset_at=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        ratio=0.9,
        pending_alert_thresholds=(0.8, 0.9),
    )

    mock_bot = AsyncMock()
    mock_config = SimpleNamespace(
        admin_ids=[1, 2],
        admin_language="en",
        timezone=timezone.utc,
    )

    with (
        patch(
            "weatherbot.infrastructure.quota_notifications.get_weather_quota_manager"
        ) as mock_get_manager,
        patch(
            "weatherbot.infrastructure.quota_notifications.get_config",
            return_value=mock_config,
        ),
        patch("weatherbot.presentation.i18n.i18n.get") as mock_i18n_get,
    ):
        manager = MagicMock()
        manager.get_status = AsyncMock(return_value=status)
        manager.mark_alert_sent = AsyncMock()
        mock_get_manager.return_value = manager

        mock_i18n_get.side_effect = lambda key, lang, **kwargs: key

        from weatherbot.infrastructure.quota_notifications import notify_quota_if_needed

        await notify_quota_if_needed(mock_bot)

    manager.get_status.assert_awaited_once()
    assert mock_bot.send_message.await_count == 4  # 2 admins * 2 thresholds
    manager.mark_alert_sent.assert_awaited_once_with(0.9, status.reset_at)


@pytest.mark.asyncio
async def test_notify_quota_without_admins_marks_threshold(tmp_path):

    status = WeatherQuotaStatus(
        limit=1000,
        used=1000,
        remaining=0,
        reset_at=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        ratio=1.0,
        pending_alert_thresholds=(1.0,),
    )

    mock_bot = AsyncMock()
    mock_config = SimpleNamespace(
        admin_ids=[], admin_language="en", timezone=timezone.utc
    )

    with (
        patch(
            "weatherbot.infrastructure.quota_notifications.get_weather_quota_manager"
        ) as mock_get_manager,
        patch(
            "weatherbot.infrastructure.quota_notifications.get_config",
            return_value=mock_config,
        ),
        patch("weatherbot.presentation.i18n.i18n.get") as mock_i18n_get,
    ):
        manager = MagicMock()
        manager.get_status = AsyncMock(return_value=status)
        manager.mark_alert_sent = AsyncMock()
        mock_get_manager.return_value = manager

        mock_i18n_get.return_value = ""

        from weatherbot.infrastructure.quota_notifications import notify_quota_if_needed

        await notify_quota_if_needed(mock_bot)

    mock_bot.send_message.assert_not_awaited()
    manager.mark_alert_sent.assert_awaited_once_with(1.0, status.reset_at)
