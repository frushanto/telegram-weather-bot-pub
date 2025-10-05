"""High-level domain events used across modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.events import Event


@dataclass(frozen=True)
class BotStarted(Event):
    version: str


@dataclass(frozen=True)
class CommandInvoked(Event):
    command: str
    user_id: Optional[int]
    chat_id: Optional[int]


@dataclass(frozen=True)
class CommandCompleted(Event):
    command: str
    duration_ms: float


@dataclass(frozen=True)
class CommandFailed(Event):
    command: str
    error: str


@dataclass(frozen=True)
class SubscriptionRestored(Event):
    chat_id: int
