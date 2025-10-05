"""Presentation layer coordinator for subscription-related flows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from weatherbot.application.interfaces import (
    ConversationStateStoreProtocol,
    SubscriptionServiceProtocol,
    UserServiceProtocol,
)
from weatherbot.core.exceptions import ValidationError
from weatherbot.domain.conversation import ConversationMode
from weatherbot.presentation.validation import SubscribeTimeModel, validate_payload

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScheduleRequest:
    """Instruction for the job queue to schedule a reminder."""

    chat_id: int
    hour: int
    minute: int


@dataclass(frozen=True, slots=True)
class SubscriptionActionResult:
    """Result envelope returned from presenter interactions."""

    message: str
    language: str
    success: bool
    schedule: Optional[ScheduleRequest] = None


class SubscriptionPresenter:
    """Coordinates subscription workflows across application services."""

    def __init__(
        self,
        subscription_service: SubscriptionServiceProtocol,
        user_service: UserServiceProtocol,
        translator: Callable[..., str],
        state_store: ConversationStateStoreProtocol,
    ) -> None:
        self._subscription_service = subscription_service
        self._user_service = user_service
        self._translate = translator
        self._state_store = state_store

    async def prompt_for_time(self, chat_id: int) -> SubscriptionActionResult:
        """Prepare prompt asking the user to provide subscription time."""

        language = await self._user_service.get_user_language(str(chat_id))

        self._state_store.set_awaiting_mode(
            chat_id, ConversationMode.AWAITING_SUBSCRIBE_TIME
        )

        message = self._translate("subscribe_prompt", language)
        return SubscriptionActionResult(
            message=message, language=language, success=True
        )

    async def subscribe(
        self,
        chat_id: int,
        time_input: str,
        *,
        clear_state: bool = False,
        validate_input: bool = True,
    ) -> SubscriptionActionResult:
        """Handle subscription creation for the provided ``time_input``."""

        language = await self._user_service.get_user_language(str(chat_id))

        if clear_state:
            self._state_store.clear_conversation(chat_id)

        try:
            if validate_input:
                payload = validate_payload(SubscribeTimeModel, time=time_input)
                normalized_time = payload.time
            else:
                normalized_time = time_input.strip()
                if not normalized_time:
                    raise ValidationError("Time value cannot be empty")
            hour, minute = await self._subscription_service.parse_time_string(
                normalized_time
            )
            await self._subscription_service.set_subscription(
                str(chat_id), hour, minute
            )
            schedule = ScheduleRequest(chat_id=chat_id, hour=hour, minute=minute)
            message = self._translate(
                "subscribe_success", language, hour=hour, minute=minute
            )
            return SubscriptionActionResult(
                message=message,
                language=language,
                success=True,
                schedule=schedule,
            )
        except ValidationError as err:
            logger.warning(
                "Validation error during subscription for %s: %s", chat_id, err
            )
            message = str(err)
            if "Home location must be set" in message:
                message = self._translate("subscribe_home_required", language)
            return SubscriptionActionResult(
                message=message, language=language, success=False
            )
        except Exception:  # pragma: no cover - defensive branch
            logger.exception("Unexpected error while subscribing user %s", chat_id)
            message = self._translate("subscribe_error", language)
            return SubscriptionActionResult(
                message=message, language=language, success=False
            )

    async def unsubscribe(self, chat_id: int) -> SubscriptionActionResult:
        """Remove existing subscription for the chat if present."""

        language = await self._user_service.get_user_language(str(chat_id))
        try:
            removed = await self._subscription_service.remove_subscription(str(chat_id))
            message_key = "unsubscribe_success" if removed else "not_subscribed"
            message = self._translate(message_key, language)
            return SubscriptionActionResult(
                message=message, language=language, success=True
            )
        except Exception:  # pragma: no cover - defensive branch
            logger.exception("Unexpected error while unsubscribing user %s", chat_id)
            message = self._translate("generic_error", language)
            return SubscriptionActionResult(
                message=message, language=language, success=False
            )


__all__ = [
    "ScheduleRequest",
    "SubscriptionActionResult",
    "SubscriptionPresenter",
]
