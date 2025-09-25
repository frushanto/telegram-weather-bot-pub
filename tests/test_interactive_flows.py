from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from weatherbot.handlers.commands import cancel_cmd, sethome_cmd, subscribe_cmd
from weatherbot.handlers.messages import on_text
from weatherbot.infrastructure.state import awaiting_sethome, awaiting_subscribe_time
from weatherbot.presentation.i18n import i18n


@pytest.mark.asyncio
async def test_sethome_interactive_prompt(monkeypatch):

    update = MagicMock()
    chat_id = 42
    update.effective_chat.id = chat_id
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"PROMPT_{key}")

    await sethome_cmd(update, context)

    assert chat_id in awaiting_sethome
    update.message.reply_text.assert_awaited_with(
        "PROMPT_sethome_prompt", reply_markup=ANY
    )


@pytest.mark.asyncio
async def test_sethome_interactive_flow(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode
    from weatherbot.infrastructure.state import conversation_manager

    chat_id = 42
    awaiting_sethome[chat_id] = True
    conversation_manager.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)

    user_service = MagicMock()
    user_service.get_user_language = AsyncMock(return_value="ru")
    user_service.set_user_home = AsyncMock()
    weather_service = MagicMock()
    weather_service.geocode_city = AsyncMock(return_value=(10.0, 20.0, "CityLabel"))
    monkeypatch.setattr(
        "weatherbot.handlers.messages.get_user_service", lambda: user_service
    )
    monkeypatch.setattr(
        "weatherbot.handlers.messages.get_weather_application_service",
        lambda: weather_service,
    )

    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = "TestCity"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"MSG_{key}")

    await on_text(update, context)

    assert chat_id not in awaiting_sethome
    assert not conversation_manager.is_awaiting(
        chat_id, ConversationMode.AWAITING_SETHOME
    )
    update.message.reply_text.assert_awaited()

    args, _ = update.message.reply_text.call_args
    assert "MSG_sethome_success" in args[0]


@pytest.mark.asyncio
async def test_subscribe_interactive_prompt(monkeypatch):

    update = MagicMock()
    chat_id = 99
    update.effective_chat.id = chat_id
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"PROMPT_{key}")

    await subscribe_cmd(update, context)

    assert chat_id in awaiting_subscribe_time
    update.message.reply_text.assert_awaited_with(
        "PROMPT_subscribe_prompt", reply_markup=ANY
    )


@pytest.mark.asyncio
async def test_subscribe_interactive_flow(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode
    from weatherbot.infrastructure.state import conversation_manager

    chat_id = 99
    awaiting_subscribe_time[chat_id] = True
    conversation_manager.set_awaiting_mode(
        chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME
    )

    sub_service = MagicMock()
    sub_service.parse_time_string = AsyncMock(return_value=(7, 30))
    sub_service.set_subscription = AsyncMock()
    monkeypatch.setattr(
        "weatherbot.handlers.messages.get_subscription_service", lambda: sub_service
    )

    # Mock user service to return home location
    user_service = MagicMock()
    user_service.get_user_home = AsyncMock(
        return_value={"latitude": 55.7558, "longitude": 37.6173, "name": "Moscow"}
    )
    user_service.get_user_language = AsyncMock(return_value="en")
    monkeypatch.setattr(
        "weatherbot.handlers.messages.get_user_service", lambda: user_service
    )

    async def mock_schedule_func(jq, cid, h, m):
        return None

    monkeypatch.setattr(
        "weatherbot.handlers.messages.schedule_daily_timezone_aware",
        mock_schedule_func,
    )

    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = "07:30"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.application.job_queue = MagicMock()

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"MSG_{key}")

    await on_text(update, context)

    assert chat_id not in awaiting_subscribe_time
    assert not conversation_manager.is_awaiting(
        chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME
    )
    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.call_args
    assert "MSG_subscribe_success" in args[0]


@pytest.mark.asyncio
async def test_cancel_clears_states(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode
    from weatherbot.infrastructure.state import conversation_manager

    chat_id = 123
    awaiting_sethome[chat_id] = True
    awaiting_subscribe_time[chat_id] = True
    conversation_manager.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)

    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = "/cancel"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"MSG_{key}")

    await on_text(update, context)

    assert chat_id not in awaiting_sethome
    assert chat_id not in awaiting_subscribe_time
    assert not conversation_manager.is_awaiting(
        chat_id, ConversationMode.AWAITING_SETHOME
    )
    update.message.reply_text.assert_awaited_with(
        "MSG_operation_cancelled", reply_markup=ANY
    )
