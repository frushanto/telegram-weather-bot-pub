import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from weatherbot.domain.conversation import ConversationMode
from weatherbot.handlers.commands import (
    CommandHandlerDependencies,
    cancel_cmd,
    configure_command_handlers,
    data_cmd,
    delete_me_cmd,
    help_cmd,
    home_cmd,
    language_cmd,
    privacy_cmd,
    sethome_cmd,
    start_cmd,
    subscribe_cmd,
    unsethome_cmd,
    unsubscribe_cmd,
    whoami_cmd,
)
from weatherbot.infrastructure.setup import get_conversation_state_store
from weatherbot.presentation.command_presenter import KeyboardView, PresenterResponse
from weatherbot.presentation.subscription_presenter import (
    ScheduleRequest,
    SubscriptionActionResult,
)


@pytest.fixture(autouse=True)
def command_handler_dependencies():
    from weatherbot.presentation.i18n import Localization

    store = get_conversation_state_store()
    presenter = SimpleNamespace(
        start=AsyncMock(),
        help=AsyncMock(),
        set_home=AsyncMock(),
        home_weather=AsyncMock(),
        unset_home=AsyncMock(),
        data_snapshot=AsyncMock(),
        delete_user_data=AsyncMock(),
        privacy=AsyncMock(),
        whoami=AsyncMock(),
    )
    subscription_presenter = SimpleNamespace(
        prompt_for_time=AsyncMock(),
        subscribe=AsyncMock(),
        unsubscribe=AsyncMock(),
    )
    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    quota_notifier = AsyncMock()
    schedule_mock = AsyncMock()
    mock_bot = AsyncMock()
    localization = Localization()

    async def quota(bot):
        await quota_notifier(bot)

    async def schedule(job_queue, chat_id, hour, minute):
        await schedule_mock(job_queue, chat_id, hour, minute)

    configure_command_handlers(
        CommandHandlerDependencies(
            command_presenter=presenter,
            subscription_presenter=subscription_presenter,
            user_service=user_service,
            state_store=store,
            quota_notifier=quota,
            schedule_subscription=schedule,
            bot=mock_bot,
            localization=localization,
        )
    )

    return SimpleNamespace(
        presenter=presenter,
        subscription_presenter=subscription_presenter,
        user_service=user_service,
        quota_notifier=quota_notifier,
        schedule_subscription=schedule_mock,
        state_store=store,
        bot=mock_bot,
        localization=localization,
    )


@pytest.fixture
def presenter_fixture(command_handler_dependencies):
    return command_handler_dependencies.presenter


@pytest.fixture
def subscription_presenter_fixture(command_handler_dependencies):
    return command_handler_dependencies.subscription_presenter


@pytest.fixture
def quota_notifier_mock(command_handler_dependencies):
    return command_handler_dependencies.quota_notifier


@pytest.fixture
def keyboard_patch(monkeypatch):
    main = MagicMock(return_value="MAIN")
    lang = MagicMock(return_value="LANG")
    monkeypatch.setattr("weatherbot.handlers.commands.main_keyboard", main)
    monkeypatch.setattr("weatherbot.handlers.commands.language_keyboard", lang)
    return main, lang


def test_start_cmd_language_prompt(presenter_fixture, keyboard_patch):
    presenter_fixture.start.return_value = PresenterResponse(
        "choose", "ru", keyboard=KeyboardView.LANGUAGE
    )

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(start_cmd(update, context))

    presenter_fixture.start.assert_awaited_once_with(123456)
    keyboard_patch[1].assert_called_once_with()
    update.message.reply_text.assert_awaited_once_with(
        "choose", reply_markup="LANG", parse_mode=None
    )


def test_start_cmd_main_keyboard(presenter_fixture, keyboard_patch):
    presenter_fixture.start.return_value = PresenterResponse("hello", "en")

    update = MagicMock()
    update.effective_chat.id = 99
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(start_cmd(update, context))

    presenter_fixture.start.assert_awaited_once_with(99)
    keyboard_patch[0].assert_called_once_with("en")
    update.message.reply_text.assert_awaited_once_with(
        "hello", reply_markup="MAIN", parse_mode=None
    )


def test_sethome_cmd_with_args(presenter_fixture, keyboard_patch):
    presenter_fixture.set_home.return_value = PresenterResponse("ok", "en")

    update = MagicMock()
    update.effective_chat.id = 7
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["New", "York"]

    asyncio.run(sethome_cmd(update, context))

    presenter_fixture.set_home.assert_awaited_once_with(7, "New York")
    update.message.reply_text.assert_awaited_once_with(
        "ok", reply_markup="MAIN", parse_mode=None
    )


def test_sethome_cmd_without_args(presenter_fixture, keyboard_patch):
    presenter_fixture.set_home.return_value = PresenterResponse(
        "prompt", "ru", keyboard=KeyboardView.MAIN
    )

    update = MagicMock()
    update.effective_chat.id = 77
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    asyncio.run(sethome_cmd(update, context))

    presenter_fixture.set_home.assert_awaited_once_with(77, None)
    update.message.reply_text.assert_awaited_once()


def test_home_cmd_notifies_quota(
    presenter_fixture, keyboard_patch, quota_notifier_mock
):
    presenter_fixture.home_weather.return_value = PresenterResponse(
        "weather", "ru", notify_quota=True
    )

    update = MagicMock()
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot = MagicMock()

    asyncio.run(home_cmd(update, context))

    presenter_fixture.home_weather.assert_awaited_once_with(123)
    quota_notifier_mock.assert_awaited_once_with(context.bot)


def test_home_cmd_without_quota_notification(
    presenter_fixture, keyboard_patch, quota_notifier_mock
):
    presenter_fixture.home_weather.return_value = PresenterResponse(
        "weather", "ru", notify_quota=False
    )

    update = MagicMock()
    update.effective_chat.id = 321
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot = MagicMock()

    asyncio.run(home_cmd(update, context))

    quota_notifier_mock.assert_not_awaited()


def test_unsethome_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.unset_home.return_value = PresenterResponse("done", "en")

    update = MagicMock()
    update.effective_chat.id = 55
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(unsethome_cmd(update, context))

    presenter_fixture.unset_home.assert_awaited_once_with(55)
    update.message.reply_text.assert_awaited_once()


def test_data_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.data_snapshot.return_value = PresenterResponse("data", "ru")

    update = MagicMock()
    update.effective_chat.id = 11
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(data_cmd(update, context))

    presenter_fixture.data_snapshot.assert_awaited_once_with(11)
    update.message.reply_text.assert_awaited_once()


def test_delete_me_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.delete_user_data.return_value = PresenterResponse("deleted", "ru")

    update = MagicMock()
    update.effective_chat.id = 22
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(delete_me_cmd(update, context))

    presenter_fixture.delete_user_data.assert_awaited_once_with(22)
    update.message.reply_text.assert_awaited_once()


def test_privacy_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.privacy.return_value = PresenterResponse("privacy", "ru")

    update = MagicMock()
    update.effective_chat.id = 44
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(privacy_cmd(update, context))

    presenter_fixture.privacy.assert_awaited_once_with(44)
    update.message.reply_text.assert_awaited_once()


def test_whoami_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.whoami.return_value = PresenterResponse("info", "en")

    update = MagicMock()
    update.effective_chat.id = 66
    update.effective_user.id = 66
    update.effective_user.first_name = "John"
    update.effective_user.last_name = "Doe"
    update.effective_user.username = "jdoe"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(whoami_cmd(update, context))

    presenter_fixture.whoami.assert_awaited_once_with(
        66, user_id=66, first_name="John", last_name="Doe", username="jdoe"
    )
    update.message.reply_text.assert_awaited_once()


def test_help_cmd(presenter_fixture, keyboard_patch):
    presenter_fixture.help.return_value = PresenterResponse("help", "ru")

    update = MagicMock()
    update.effective_chat.id = 42
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(help_cmd(update, context))

    presenter_fixture.help.assert_awaited_once_with(42)
    update.message.reply_text.assert_awaited_once()


def test_subscribe_cmd(subscription_presenter_fixture):
    subscription_presenter_fixture.subscribe.return_value = SubscriptionActionResult(
        "ok", "ru", success=True, schedule=ScheduleRequest(123456, 8, 30)
    )

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["8:30"]
    context.application.job_queue = MagicMock()

    asyncio.run(subscribe_cmd(update, context))

    subscription_presenter_fixture.subscribe.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()


def test_language_cmd(command_handler_dependencies):
    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["en"]

    asyncio.run(language_cmd(update, context))

    command_handler_dependencies.user_service.set_user_language.assert_awaited_once_with(
        "123456", "en"
    )
    update.message.reply_text.assert_awaited_once()


def test_unsubscribe_cmd(subscription_presenter_fixture):
    subscription_presenter_fixture.unsubscribe.return_value = PresenterResponse(
        "done", "ru"
    )

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.application.job_queue.get_jobs_by_name.return_value = []

    asyncio.run(unsubscribe_cmd(update, context))

    subscription_presenter_fixture.unsubscribe.assert_awaited_once_with(123456)
    update.message.reply_text.assert_awaited_once()


def test_cancel_cmd_clears_state(command_handler_dependencies):
    store = command_handler_dependencies.state_store
    store.set_awaiting_mode(1, ConversationMode.AWAITING_CITY_WEATHER)

    update = MagicMock()
    update.effective_chat.id = 1
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    command_handler_dependencies.user_service.get_user_language.return_value = "ru"

    asyncio.run(cancel_cmd(update, context))

    assert not store.is_awaiting(1, ConversationMode.AWAITING_CITY_WEATHER)
    update.message.reply_text.assert_awaited_once()
