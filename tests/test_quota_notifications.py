import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from weatherbot.infrastructure.quota_notifications import QuotaNotifier
from weatherbot.infrastructure.weather_quota import WeatherQuotaStatus


def test_notify_quota_sends_alerts_and_marks(tmp_path):

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

    localization = MagicMock()
    localization.get.side_effect = lambda key, lang, **kwargs: key

    manager = MagicMock()
    manager.get_status = AsyncMock(return_value=status)
    manager.mark_alert_sent = AsyncMock()

    notifier = QuotaNotifier(
        quota_manager=manager,
        localization=localization,
        config_provider=lambda: mock_config,
    )

    asyncio.run(notifier(mock_bot))

    manager.get_status.assert_awaited_once()
    assert mock_bot.send_message.await_count == 4  # 2 admins * 2 thresholds
    manager.mark_alert_sent.assert_awaited_once_with(0.9, status.reset_at)


def test_notify_quota_without_admins_marks_threshold(tmp_path):

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

    localization = MagicMock()
    localization.get.return_value = ""

    manager = MagicMock()
    manager.get_status = AsyncMock(return_value=status)
    manager.mark_alert_sent = AsyncMock()

    notifier = QuotaNotifier(
        quota_manager=manager,
        localization=localization,
        config_provider=lambda: mock_config,
    )

    asyncio.run(notifier(mock_bot))

    mock_bot.send_message.assert_not_awaited()
    manager.mark_alert_sent.assert_awaited_once_with(1.0, status.reset_at)
