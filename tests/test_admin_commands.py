import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz

from weatherbot.application.admin_service import (
    AdminConfigSnapshot,
    AdminQuotaStatus,
    AdminStatsResult,
    AdminSubscriptionEntry,
    AdminSubscriptionsResult,
    AdminTestWeatherResult,
    AdminTopUser,
    AdminUserInfo,
)
from weatherbot.domain.weather import WeatherCurrent, WeatherDaily, WeatherReport
from weatherbot.presentation.i18n import Localization


@pytest.fixture(autouse=True)
def stub_admin_only(monkeypatch):
    def decorator_factory(_ids):
        def decorator(func):
            return func

        return decorator

    monkeypatch.setattr("weatherbot.core.decorators.admin_only", decorator_factory)


@pytest.fixture
def admin_handlers(monkeypatch):
    if "weatherbot.handlers.admin_commands" in sys.modules:
        del sys.modules["weatherbot.handlers.admin_commands"]

    import weatherbot.handlers.admin_commands as admin_cmd

    service = AsyncMock()
    localization = Localization()
    config = SimpleNamespace(
        admin_ids={1}, admin_language="ru", timezone=pytz.timezone("UTC")
    )

    admin_cmd.configure_admin_handlers(
        admin_cmd.AdminHandlerDependencies(
            admin_service=service,
            localization=localization,
            config_provider=lambda: config,
        )
    )

    return service, admin_cmd


@pytest.mark.asyncio
async def test_admin_stats_functionality(admin_handlers):
    service, admin_cmd = admin_handlers
    service.get_stats.return_value = AdminStatsResult(
        user_count=3,
        blocked_count=1,
        top_users=[
            AdminTopUser(user_id=3, daily_requests=200, is_blocked=True),
            AdminTopUser(user_id=2, daily_requests=50, is_blocked=False),
        ],
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_stats_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    message = update.message.reply_text.await_args.args[0]
    assert "Всего пользователей: 3" in message
    assert "Заблокированных: 1" in message
    assert "ID 3: 200" in message
    assert "ID 2: 50" in message


@pytest.mark.asyncio
async def test_admin_unblock_success(admin_handlers):
    service, admin_cmd = admin_handlers
    service.unblock_user.return_value = True

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["123456789"]

    await admin_cmd.admin_unblock_cmd(update, context)

    service.unblock_user.assert_awaited_once_with(123456789)
    update.message.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_admin_unblock_usage(admin_handlers):
    _service, admin_cmd = admin_handlers
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    await admin_cmd.admin_unblock_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "/admin_unblock" in update.message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_admin_cleanup_triggers_service(admin_handlers):
    service, admin_cmd = admin_handlers
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_cleanup_cmd(update, context)

    service.cleanup_spam.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_backup_now(admin_handlers):
    service, admin_cmd = admin_handlers
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_backup_now_cmd(update, context)

    service.run_manual_backup.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_subscriptions_list(admin_handlers):
    service, admin_cmd = admin_handlers
    service.list_subscriptions.return_value = AdminSubscriptionsResult(
        total=2,
        items=[
            AdminSubscriptionEntry(
                chat_id="100",
                hour=7,
                minute=30,
                label="Berlin",
                timezone="Europe/Berlin",
            ),
            AdminSubscriptionEntry(
                chat_id="200", hour=9, minute=0, label=None, timezone=None
            ),
        ],
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_subscriptions_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    text = update.message.reply_text.await_args.args[0]
    assert "📬" in text
    assert "#100" in text
    assert "#200" in text


@pytest.mark.asyncio
async def test_admin_subscriptions_empty(admin_handlers):
    service, admin_cmd = admin_handlers
    service.list_subscriptions.return_value = AdminSubscriptionsResult(
        total=0, items=[]
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_subscriptions_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    assert (
        "Активных подписок не найдено" in update.message.reply_text.await_args.args[0]
    )


@pytest.mark.asyncio
async def test_admin_config_snapshot(admin_handlers, monkeypatch):
    service, admin_cmd = admin_handlers
    service.get_runtime_config.return_value = AdminConfigSnapshot(
        timezone="Europe/Berlin",
        storage_path="data/storage.json",
        backup_enabled=True,
        backup_hour=3,
        backup_retention_days=30,
        spam_limits=(10, 100, 500),
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_config_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    sent = update.message.reply_text.await_args.kwargs.get("text")
    if sent is None:
        sent = update.message.reply_text.await_args.args[0]
    assert "Runtime configuration" in sent or "Текущая конфигурация" in sent


@pytest.mark.asyncio
async def test_admin_test_weather_success(admin_handlers):
    service, admin_cmd = admin_handlers
    service.test_weather.return_value = AdminTestWeatherResult(
        place_label="Berlin",
        weather_data=_admin_sample_report(),
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["Berlin"]

    with patch(
        "weatherbot.presentation.formatter.format_weather",
        return_value="FORMATTED",
    ):
        await admin_cmd.admin_test_weather_cmd(update, context)

    service.test_weather.assert_awaited_once_with("Berlin")
    update.message.reply_text.assert_awaited_once()
    assert (
        "FORMATTED" in update.message.reply_text.await_args.kwargs.get("text", "")
        or "FORMATTED" in update.message.reply_text.await_args.args[0]
    )


@pytest.mark.asyncio
async def test_admin_test_weather_usage(admin_handlers):
    service, admin_cmd = admin_handlers

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    await admin_cmd.admin_test_weather_cmd(update, context)

    service.test_weather.assert_not_called()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_test_weather_not_found(admin_handlers):
    from weatherbot.core.exceptions import GeocodeServiceError

    service, admin_cmd = admin_handlers
    service.test_weather.side_effect = GeocodeServiceError("not found")

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["Atlantis"]

    await admin_cmd.admin_test_weather_cmd(update, context)

    service.test_weather.assert_awaited_once_with("Atlantis")
    sent = update.message.reply_text.await_args.args[0]
    assert "Atlantis" in sent


@pytest.mark.asyncio
async def test_admin_quota_functionality(admin_handlers, monkeypatch):
    service, admin_cmd = admin_handlers
    status = AdminQuotaStatus(
        limit=10,
        used=8,
        remaining=2,
        reset_at=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        ratio=0.8,
    )
    service.get_quota_status.return_value = status

    config_stub = SimpleNamespace(
        admin_ids={1}, admin_language="ru", timezone=timezone.utc
    )
    admin_cmd.configure_admin_handlers(
        admin_cmd.AdminHandlerDependencies(
            admin_service=service,
            localization=Localization(),
            config_provider=lambda: config_stub,
        )
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_quota_cmd(update, context)

    service.get_quota_status.assert_awaited_once()
    text = update.message.reply_text.await_args.kwargs.get("text")
    if text is None:
        text = update.message.reply_text.await_args.args[0]
    assert "{used}/{limit}".format(used=8, limit=10) in text or "8/10" in text


@pytest.mark.asyncio
async def test_admin_help_lists_commands(admin_handlers):
    _service, admin_cmd = admin_handlers

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await admin_cmd.admin_help_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    text = update.message.reply_text.await_args.kwargs.get("text")
    if text is None:
        text = update.message.reply_text.await_args.args[0]
    assert "admin_subscriptions" in text
    assert "admin_quota" in text


@pytest.mark.asyncio
async def test_admin_user_info(admin_handlers):
    service, admin_cmd = admin_handlers
    service.get_user_info.return_value = AdminUserInfo(
        requests_today=5,
        is_blocked=True,
        block_count=2,
        blocked_until=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
    )

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["42"]

    await admin_cmd.admin_user_info_cmd(update, context)

    service.get_user_info.assert_awaited_once_with(42)
    text = update.message.reply_text.await_args.args[0]
    assert "Запросов сегодня" in text or "Requests today" in text


@pytest.mark.asyncio
async def test_admin_user_info_usage(admin_handlers):
    _service, admin_cmd = admin_handlers

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    await admin_cmd.admin_user_info_cmd(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "/admin_user_info" in update.message.reply_text.await_args.args[0]


def _admin_sample_report() -> WeatherReport:
    return WeatherReport(
        current=WeatherCurrent(
            temperature=10.0,
            apparent_temperature=9.0,
            wind_speed=2.0,
            weather_code=1,
        ),
        daily=[
            WeatherDaily(
                min_temperature=5.0,
                max_temperature=12.0,
                precipitation_probability=40.0,
                sunrise="2025-01-01T07:00",
                sunset="2025-01-01T16:00",
                wind_speed_max=3.5,
                weather_code=2,
            )
        ],
    )
