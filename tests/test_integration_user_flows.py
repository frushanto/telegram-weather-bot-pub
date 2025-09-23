from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ContextTypes

from weatherbot.handlers.commands import (
    home_cmd,
    sethome_cmd,
    subscribe_cmd,
    unsethome_cmd,
    unsubscribe_cmd,
)
from weatherbot.handlers.messages import on_text
from weatherbot.presentation.keyboards import main_keyboard


@pytest.mark.asyncio
async def test_sethome_home_unsethome_flow():
    update = MagicMock()
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    context.args = []

    with (
        patch("weatherbot.handlers.commands.get_user_service") as mock_user_svc,
        patch(
            "weatherbot.handlers.commands.get_weather_application_service"
        ) as mock_weather_svc,
        patch(
            "weatherbot.handlers.commands.format_weather", return_value="WEATHER_MSG"
        ),
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        user_service.set_user_home = AsyncMock()
        user_service.get_user_home.return_value = {
            "lat": 10,
            "lon": 20,
            "label": "TestCity",
        }
        mock_user_svc.return_value = user_service

        weather_service = AsyncMock()
        weather_service.geocode_city.return_value = (10, 20, "TestCity")
        weather_service.get_weather_by_coordinates.return_value = {}
        mock_weather_svc.return_value = weather_service

        await sethome_cmd.__wrapped__(update, context)
        update.message.reply_text.assert_awaited()
        update.message.reply_text.reset_mock()

        context.args = ["TestCity"]
        await sethome_cmd.__wrapped__(update, context)
        user_service.set_user_home.assert_awaited_once_with(
            str(123), 10, 20, "TestCity"
        )
        update.message.reply_text.assert_awaited()
        update.message.reply_text.reset_mock()

        await home_cmd.__wrapped__(update, context)
        update.message.reply_text.assert_awaited_once_with(
            "WEATHER_MSG", parse_mode="HTML", reply_markup=main_keyboard("ru")
        )
        update.message.reply_text.reset_mock()

        user_service.remove_user_home.return_value = True
        await unsethome_cmd.__wrapped__(update, context)
        update.message.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_flow():
    update = MagicMock()
    update.effective_chat.id = 456
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    context.args = []
    with (
        patch("weatherbot.handlers.commands.get_user_service") as mock_user_svc,
        patch("weatherbot.handlers.commands.get_subscription_service") as mock_sub_svc,
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "en"
        mock_user_svc.return_value = user_service

        sub_service = AsyncMock()
        sub_service.parse_time_string.return_value = (8, 0)
        sub_service.set_subscription = AsyncMock()
        mock_sub_svc.return_value = sub_service

        await subscribe_cmd.__wrapped__(update, context)
        update.message.reply_text.assert_awaited()
        update.message.reply_text.reset_mock()

        context.args = ["08:00"]
        await subscribe_cmd.__wrapped__(update, context)
        sub_service.set_subscription.assert_awaited_once_with(str(456), 8, 0)
        update.message.reply_text.assert_awaited()
        update.message.reply_text.reset_mock()

        await unsubscribe_cmd.__wrapped__(update, context)
        update.message.reply_text.assert_awaited()
