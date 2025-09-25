"""Conversation state value objects and manager for handler interactions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class ConversationMode(Enum):
    """Types of conversational states the bot can be in."""

    IDLE = "idle"
    AWAITING_SETHOME = "awaiting_sethome"
    AWAITING_CITY_WEATHER = "awaiting_city_weather"
    AWAITING_SUBSCRIBE_TIME = "awaiting_subscribe_time"
    AWAITING_LANGUAGE_INPUT = "awaiting_language_input"


@dataclass
class LocationContext:
    """Stores temporary location data during conversations."""

    latitude: float
    longitude: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)

    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> LocationContext:
        return cls(latitude=coords[0], longitude=coords[1])


@dataclass
class ConversationState:
    """Represents the current conversation state for a chat."""

    mode: ConversationMode = ConversationMode.IDLE
    last_location: Optional[LocationContext] = None

    def is_awaiting(self, mode: ConversationMode) -> bool:
        """Check if currently in a specific awaiting mode."""
        return self.mode == mode

    def set_awaiting(self, mode: ConversationMode) -> ConversationState:
        """Return new state with updated mode."""
        return ConversationState(mode=mode, last_location=self.last_location)

    def set_location(self, lat: float, lon: float) -> ConversationState:
        """Return new state with updated location context."""
        location = LocationContext(latitude=lat, longitude=lon)
        return ConversationState(mode=self.mode, last_location=location)

    def clear(self) -> ConversationState:
        """Return new idle state, preserving location context."""
        return ConversationState(
            mode=ConversationMode.IDLE, last_location=self.last_location
        )

    def to_storage(self) -> Dict[str, Any]:
        """Serialize for storage (if needed for persistence)."""
        data = {"mode": self.mode.value}
        if self.last_location:
            data["last_location"] = {
                "lat": self.last_location.latitude,
                "lon": self.last_location.longitude,
            }
        return data

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> ConversationState:
        """Deserialize from storage."""
        mode_str = data.get("mode", ConversationMode.IDLE.value)
        try:
            mode = ConversationMode(mode_str)
        except ValueError:
            mode = ConversationMode.IDLE

        last_location = None
        if loc_data := data.get("last_location"):
            try:
                last_location = LocationContext(
                    latitude=float(loc_data["lat"]), longitude=float(loc_data["lon"])
                )
            except (KeyError, TypeError, ValueError):
                pass

        return cls(mode=mode, last_location=last_location)


class ConversationStateManager:
    """Manages conversation state for all chats."""

    def __init__(self):
        self._states: Dict[int, ConversationState] = {}

    def get_state(self, chat_id: int) -> ConversationState:
        """Get current conversation state for a chat."""
        return self._states.get(chat_id, ConversationState())

    def set_state(self, chat_id: int, state: ConversationState) -> None:
        """Update conversation state for a chat."""
        if state.mode == ConversationMode.IDLE and not state.last_location:
            # Clean up idle states with no location context
            self._states.pop(chat_id, None)
        else:
            self._states[chat_id] = state

    def set_awaiting_mode(self, chat_id: int, mode: ConversationMode) -> None:
        """Set chat to a specific awaiting mode."""
        current = self.get_state(chat_id)
        self.set_state(chat_id, current.set_awaiting(mode))

    def set_location(self, chat_id: int, lat: float, lon: float) -> None:
        """Store location context for a chat."""
        current = self.get_state(chat_id)
        self.set_state(chat_id, current.set_location(lat, lon))

    def clear_conversation(self, chat_id: int) -> None:
        """Reset chat to idle mode."""
        current = self.get_state(chat_id)
        self.set_state(chat_id, current.clear())

    def is_awaiting(self, chat_id: int, mode: ConversationMode) -> bool:
        """Check if chat is in a specific awaiting mode."""
        return self.get_state(chat_id).is_awaiting(mode)

    def get_last_location(self, chat_id: int) -> Optional[Tuple[float, float]]:
        """Get last location as tuple (for backward compatibility)."""
        state = self.get_state(chat_id)
        return state.last_location.to_tuple() if state.last_location else None

    def cleanup_all(self) -> None:
        """Clear all conversation states (for tests)."""
        self._states.clear()
