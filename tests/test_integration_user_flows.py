from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ContextTypes

from weatherbot.domain.value_objects import UserHome
from weatherbot.domain.weather import WeatherCurrent, WeatherDaily, WeatherReport
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

    from weatherbot.handlers import commands
    from weatherbot.presentation.command_presenter import (
        KeyboardView,
        PresenterResponse,
    )

    # stub presenter.set_home for prompt and success flow
    commands._deps.command_presenter.set_home = AsyncMock(
        return_value=PresenterResponse(
            message="Prompt for city", language="ru", keyboard=KeyboardView.MAIN
        )
    )

    # prompt flow
    await sethome_cmd.__wrapped__(update, context)
    update.message.reply_text.assert_awaited()
    update.message.reply_text.reset_mock()

    # success flow
    commands._deps.command_presenter.set_home = AsyncMock(
        return_value=PresenterResponse(
            message="Home set successfully", language="ru", keyboard=KeyboardView.MAIN
        )
    )
    context.args = ["TestCity"]
    await sethome_cmd.__wrapped__(update, context)
    commands._deps.command_presenter.set_home.assert_awaited_with(123, "TestCity")
    update.message.reply_text.assert_awaited()
    update.message.reply_text.reset_mock()

    # home flow
    commands._deps.command_presenter.home_weather = AsyncMock(
        return_value=PresenterResponse(
            message="HOME_MSG",
            language="ru",
            keyboard=KeyboardView.MAIN,
            parse_mode="HTML",
        )
    )
    await home_cmd.__wrapped__(update, context)
    commands._deps.command_presenter.home_weather.assert_awaited_with(123)
    update.message.reply_text.assert_awaited_once_with(
        "HOME_MSG", parse_mode="HTML", reply_markup=main_keyboard("ru")
    )
    update.message.reply_text.reset_mock()

    # unset flow
    commands._deps.command_presenter.unset_home = AsyncMock(
        return_value=PresenterResponse(
            message="Unset OK", language="ru", keyboard=KeyboardView.MAIN
        )
    )
    await unsethome_cmd.__wrapped__(update, context)
    commands._deps.command_presenter.unset_home.assert_awaited_with(123)
    update.message.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_flow():
    update = MagicMock()
    update.effective_chat.id = 456
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    from weatherbot.handlers import commands
    from weatherbot.presentation.command_presenter import (
        KeyboardView,
        PresenterResponse,
    )

    # prompt flow (no args)
    context.args = []
    commands._deps.subscription_presenter.prompt_for_time = AsyncMock(
        return_value=PresenterResponse(
            message="Please send time", language="en", keyboard=KeyboardView.MAIN
        )
    )
    await subscribe_cmd.__wrapped__(update, context)
    commands._deps.subscription_presenter.prompt_for_time.assert_awaited_with(456)
    update.message.reply_text.assert_awaited()
    update.message.reply_text.reset_mock()

    # subscribe flow with args
    context.args = ["08:00"]
    commands._deps.subscription_presenter.subscribe = AsyncMock(
        return_value=PresenterResponse(
            message="Subscribed", language="en", keyboard=KeyboardView.MAIN
        )
    )
    await subscribe_cmd.__wrapped__(update, context)
    commands._deps.subscription_presenter.subscribe.assert_awaited_with(
        456, "08:00", validate_input=False
    )
    update.message.reply_text.assert_awaited()
    update.message.reply_text.reset_mock()

    # unsubscribe flow
    commands._deps.subscription_presenter.unsubscribe = AsyncMock(
        return_value=PresenterResponse(
            message="Unsubscribed", language="en", keyboard=KeyboardView.MAIN
        )
    )
    await unsubscribe_cmd.__wrapped__(update, context)
    commands._deps.subscription_presenter.unsubscribe.assert_awaited_with(456)
    update.message.reply_text.assert_awaited()
