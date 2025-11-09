import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytz

from weatherbot.core.exceptions import WeatherServiceError
from weatherbot.jobs import scheduler


@pytest.mark.asyncio
async def test_send_home_weather_retries_and_falls_back(monkeypatch):
    # Arrange dependencies
    user_service = AsyncMock()
    user_service.get_user_home.return_value = SimpleNamespace(
        lat=1.0, lon=2.0, label="Test", timezone="Europe/Berlin"
    )
    user_service.get_user_language.return_value = "en"

    weather_service = AsyncMock()
    # Fail twice, then keep failing to trigger fallback
    weather_service.get_weather_by_coordinates.side_effect = WeatherServiceError(
        "temporarily unavailable"
    )

    quota_notifier = AsyncMock()

    def weather_formatter(*args, **kwargs):
        return "formatted"

    def translate(key, lang, **kwargs):
        return key

    scheduler.configure_scheduler(
        scheduler.SchedulerDependencies(
            user_service=user_service,
            weather_service=weather_service,
            quota_notifier=lambda bot: quota_notifier(bot),
            weather_formatter=weather_formatter,
            translate=translate,
            config_provider=lambda: SimpleNamespace(
                timezone=pytz.UTC,
                schedule_weather_retry_attempts=2,
                schedule_weather_retry_delay_sec=0,
            ),
        )
    )

    # Fake context with bot and job
    class DummyBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append((chat_id, text, kwargs))

    class DummyJob:
        def __init__(self, chat_id):
            self.chat_id = chat_id

    class DummyContext:
        def __init__(self, chat_id):
            self.bot = DummyBot()
            self.job = DummyJob(chat_id)

    ctx = DummyContext(chat_id=123)

    # Act
    await scheduler.send_home_weather(ctx)

    # Assert: after retries, a fallback message is sent with our key
    assert len(ctx.bot.sent) == 1
    chat_id, text, _ = ctx.bot.sent[0]
    assert chat_id == 123
    assert text == "weather_service_unavailable"
    # Ensure weather fetch attempted "attempts" times
    assert weather_service.get_weather_by_coordinates.await_count == 2
