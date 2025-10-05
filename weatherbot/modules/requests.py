"""Mediator request objects used between modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict

from telegram import Update
from telegram.ext import Application, ContextTypes

from ..core.events import Request


@dataclass(frozen=True)
class GetAdminCommandMap(Request):
    """Retrieve a mapping of admin command names to their callables."""


AdminCommand = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[object] | object]
AdminCommandMap = Dict[str, AdminCommand]


@dataclass(frozen=True)
class RestoreSubscriptions(Request):
    application: Application
