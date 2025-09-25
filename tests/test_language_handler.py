from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.domain.value_objects import UserProfile
from weatherbot.handlers.language import language_callback


@pytest.mark.asyncio
async def test_language_callback_success():

    update = MagicMock()
    update.callback_query.data = "lang_en"
    update.effective_chat.id = 123456
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    context = MagicMock()
    context.bot = AsyncMock()
    with (
        patch("weatherbot.handlers.language.get_user_service") as mock_user_service,
        patch("weatherbot.handlers.language.i18n.get") as mock_i18n,
    ):
        user_service = AsyncMock()
        user_service.set_user_language = AsyncMock()
        user_service.get_user_profile.return_value = UserProfile(
            language="en", language_explicit=True
        )
        mock_user_service.return_value = user_service
        mock_i18n.return_value = "Language changed to English"
        await language_callback(update, context)

    user_service.set_user_language.assert_awaited_once_with("123456", "en")
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_language_callback_all_languages():

    languages = ["ru", "en", "de"]
    for lang in languages:
        update = MagicMock()
        update.callback_query.data = f"lang_{lang}"
        update.effective_chat.id = 123456
        update.callback_query.answer = AsyncMock()
        update.callback_query.message.edit_text = AsyncMock()
        context = MagicMock()
        context.bot = AsyncMock()
        with (
            patch("weatherbot.handlers.language.get_user_service") as mock_user_service,
            patch("weatherbot.handlers.language.i18n.get") as mock_i18n,
        ):
            user_service = AsyncMock()
            user_service.set_user_language = AsyncMock()
            user_service.get_user_profile.return_value = UserProfile(
                language=lang, language_explicit=True
            )
            mock_user_service.return_value = user_service
            mock_i18n.return_value = f"Language changed to {lang}"
            await language_callback(update, context)

        user_service.set_user_language.assert_awaited_once_with("123456", lang)
        user_service.set_user_language.reset_mock()


@pytest.mark.asyncio
async def test_language_callback_invalid_data():

    update = MagicMock()
    update.callback_query.data = "invalid_data"
    update.callback_query.answer = AsyncMock()
    context = MagicMock()
    await language_callback(update, context)

    update.callback_query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_language_callback_no_callback_query():

    update = MagicMock()
    update.callback_query = None
    context = MagicMock()

    await language_callback(update, context)


@pytest.mark.asyncio
async def test_language_callback_service_error():

    update = MagicMock()
    update.callback_query.data = "lang_en"
    update.effective_chat.id = 123456
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    context = MagicMock()
    context.bot = AsyncMock()
    with (
        patch("weatherbot.handlers.language.get_user_service") as mock_user_service,
        patch("weatherbot.handlers.language.i18n.get") as mock_i18n,
    ):
        user_service = AsyncMock()
        user_service.get_user_profile.return_value = UserProfile()
        user_service.set_user_language.side_effect = Exception("Database error")
        mock_user_service.return_value = user_service
        mock_i18n.return_value = "❌ Ошибка при смене языка"
        await language_callback(update, context)

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.message.edit_text.assert_awaited_once()
    call_args = update.callback_query.message.edit_text.await_args[0][0]
    assert "Ошибка" in call_args
