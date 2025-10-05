from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from weatherbot.application.dtos import GeocodeResultDTO
from weatherbot.domain.conversation import ConversationMode
from weatherbot.handlers.commands import cancel_cmd, sethome_cmd, subscribe_cmd
from weatherbot.handlers.messages import on_text
from weatherbot.infrastructure.setup import get_conversation_state_store
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

    state_store = get_conversation_state_store()

    from weatherbot.handlers import commands
    from weatherbot.presentation.command_presenter import (
        KeyboardView,
        PresenterResponse,
    )

    # stub presenter.set_home to mutate state and return prompt
    async def fake_set_home(chat_id, city_input=None):
        store = get_conversation_state_store()
        store.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)
        return PresenterResponse(
            message="Choose time for daily weather forecast:",
            language="ru",
            keyboard=KeyboardView.MAIN,
        )

    commands._deps.command_presenter.set_home = AsyncMock(side_effect=fake_set_home)
    await sethome_cmd(update, context)

    assert state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SETHOME)
    # The handler may include an explicit parse_mode kw (often None). Tests should
    # focus on the meaningful parts of the call (text and reply_markup) and not
    # be brittle about presence of optional kwargs like parse_mode.
    update.message.reply_text.assert_awaited()
    args, kwargs = update.message.reply_text.call_args
    # Since we're using presenter pattern, the message comes from the presenter, not i18n
    assert args[0] == "Choose time for daily weather forecast:"
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_sethome_interactive_flow(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode

    state_store = get_conversation_state_store()

    chat_id = 42
    state_store.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)

    user_service = MagicMock()
    user_service.get_user_language = AsyncMock(return_value="ru")
    user_service.set_user_home = AsyncMock()
    weather_service = MagicMock()
    weather_service.geocode_city = AsyncMock(
        return_value=GeocodeResultDTO(lat=10.0, lon=20.0, label="CityLabel")
    )
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

    assert not state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SETHOME)
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

    state_store = get_conversation_state_store()

    from weatherbot.handlers import commands
    from weatherbot.presentation.command_presenter import (
        KeyboardView,
        PresenterResponse,
    )
    from weatherbot.presentation.subscription_presenter import SubscriptionActionResult

    # stub subscription_presenter.prompt_for_time to set state and return prompt
    async def fake_prompt(cid):
        state_store.set_awaiting_mode(cid, ConversationMode.AWAITING_SUBSCRIBE_TIME)
        return SubscriptionActionResult(
            message="PROMPT_subscribe_prompt", language="ru", success=True
        )

    commands._deps.subscription_presenter.prompt_for_time = AsyncMock(
        side_effect=fake_prompt
    )
    await subscribe_cmd(update, context)

    assert state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME)
    update.message.reply_text.assert_awaited_with(
        "PROMPT_subscribe_prompt", reply_markup=ANY
    )


@pytest.mark.asyncio
async def test_subscribe_interactive_flow(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode

    state_store = get_conversation_state_store()

    chat_id = 99
    state_store.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME)

    from weatherbot.handlers import commands
    from weatherbot.presentation.subscription_presenter import SubscriptionActionResult

    # stub subscription_presenter.subscribe to clear state
    async def fake_subscribe(
        chat_id, time_input, clear_state=False, validate_input=True
    ):
        store = get_conversation_state_store()
        store.clear_conversation(chat_id)
        return SubscriptionActionResult(
            message=i18n.get("subscribe_success", "en"), language="en", success=True
        )

    commands._deps.subscription_presenter.subscribe = AsyncMock(
        side_effect=fake_subscribe
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

    assert not state_store.is_awaiting(
        chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME
    )
    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.call_args
    assert "MSG_subscribe_success" in args[0]


@pytest.mark.asyncio
async def test_cancel_clears_states(monkeypatch):
    from weatherbot.domain.conversation import ConversationMode

    state_store = get_conversation_state_store()

    chat_id = 123
    state_store.set_awaiting_mode(chat_id, ConversationMode.AWAITING_SETHOME)

    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = "/cancel"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    monkeypatch.setattr(i18n, "get", lambda key, lang, **kwargs: f"MSG_{key}")

    await on_text(update, context)

    assert not state_store.is_awaiting(chat_id, ConversationMode.AWAITING_SETHOME)
    update.message.reply_text.assert_awaited_with(
        "MSG_operation_cancelled", reply_markup=ANY
    )
