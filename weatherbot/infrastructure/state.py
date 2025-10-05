from dataclasses import dataclass, field
from typing import Optional, Tuple

from ..application.interfaces import ConversationStateStoreProtocol
from ..domain.conversation import (
    ConversationMode,
    ConversationState,
    ConversationStateManager,
)


@dataclass
class ConversationStateStore(ConversationStateStoreProtocol):
    conversation_manager: ConversationStateManager = field(
        default_factory=ConversationStateManager
    )

    def get_state(self, chat_id: int) -> ConversationState:
        return self.conversation_manager.get_state(chat_id)

    def set_state(self, chat_id: int, state: ConversationState) -> None:
        self.conversation_manager.set_state(chat_id, state)

    def set_awaiting_mode(self, chat_id: int, mode: ConversationMode) -> None:
        self.conversation_manager.set_awaiting_mode(chat_id, mode)

    def set_location(self, chat_id: int, lat: float, lon: float) -> None:
        self.conversation_manager.set_location(chat_id, lat, lon)

    def clear_conversation(self, chat_id: int) -> None:
        self.conversation_manager.clear_conversation(chat_id)

    def is_awaiting(self, chat_id: int, mode: ConversationMode) -> bool:
        return self.conversation_manager.is_awaiting(chat_id, mode)

    def get_last_location(self, chat_id: int) -> Optional[Tuple[float, float]]:
        return self.conversation_manager.get_last_location(chat_id)

    def reset(self) -> None:
        self.conversation_manager.cleanup_all()
