import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.domain.value_objects import UserProfile
from weatherbot.presentation.i18n import Localization


@pytest.fixture
def language_dependencies():
    if "weatherbot.handlers.language" in sys.modules:
        del sys.modules["weatherbot.handlers.language"]

    import weatherbot.handlers.language as language_module

    user_service = AsyncMock()
    localization = Localization()
    keyboard_factory = MagicMock(return_value=None)

    language_module.configure_language_handlers(
        language_module.LanguageHandlerDependencies(
            user_service=user_service,
            localization=localization,
            keyboard_factory=keyboard_factory,
        )
    )

    return language_module, user_service, keyboard_factory


@pytest.mark.asyncio
async def test_language_callback_success(language_dependencies):

    module, user_service, keyboard_factory = language_dependencies
    update = MagicMock()
    update.callback_query.data = "lang_en"
    update.effective_chat.id = 123456
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    context = MagicMock()
    context.bot = AsyncMock()

    user_service.get_user_profile.return_value = UserProfile(
        language="en", language_explicit=True
    )

    await module.language_callback(update, context)

    user_service.set_user_language.assert_awaited_once_with("123456", "en")
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.message.edit_text.assert_awaited_once()
    keyboard_factory.assert_not_called()


@pytest.mark.asyncio
async def test_language_callback_all_languages(language_dependencies):

    module, user_service, _keyboard_factory = language_dependencies

    for lang in ["ru", "en", "de"]:
        update = MagicMock()
        update.callback_query.data = f"lang_{lang}"
        update.effective_chat.id = 123456
        update.callback_query.answer = AsyncMock()
        update.callback_query.message.edit_text = AsyncMock()
        context = MagicMock()
        context.bot = AsyncMock()

        user_service.get_user_profile.return_value = UserProfile(
            language=lang, language_explicit=True
        )

        await module.language_callback(update, context)

        user_service.set_user_language.assert_awaited_once_with("123456", lang)
        user_service.set_user_language.reset_mock()


@pytest.mark.asyncio
async def test_language_callback_invalid_data(language_dependencies):

    module, _user_service, _keyboard_factory = language_dependencies
    update = MagicMock()
    update.callback_query.data = "invalid_data"
    update.callback_query.answer = AsyncMock()
    context = MagicMock()

    await module.language_callback(update, context)

    update.callback_query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_language_callback_no_callback_query(language_dependencies):

    module, _user_service, _keyboard_factory = language_dependencies
    update = MagicMock()
    update.callback_query = None
    context = MagicMock()

    await module.language_callback(update, context)


@pytest.mark.asyncio
async def test_language_callback_service_error(language_dependencies):

    module, user_service, _keyboard_factory = language_dependencies
    update = MagicMock()
    update.callback_query.data = "lang_en"
    update.effective_chat.id = 123456
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    context = MagicMock()
    context.bot = AsyncMock()

    user_service.get_user_profile.return_value = UserProfile()
    user_service.set_user_language.side_effect = Exception("Database error")

    await module.language_callback(update, context)

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.message.edit_text.assert_awaited_once()
    call_args = update.callback_query.message.edit_text.await_args[0][0]
    assert "Ошибка" in call_args
