"""Bot composition modules."""

from .admin_module import AdminModule
from .base import Module, ModuleContext, ModuleLoader
from .command_module import CommandModule
from .events import (
    BotStarted,
    CommandCompleted,
    CommandFailed,
    CommandInvoked,
    SubscriptionRestored,
)
from .jobs_module import JobsModule
from .observability import ObservabilityModule
from .requests import GetAdminCommandMap, RestoreSubscriptions

__all__ = [
    "AdminModule",
    "Module",
    "ModuleContext",
    "ModuleLoader",
    "CommandModule",
    "JobsModule",
    "ObservabilityModule",
    "GetAdminCommandMap",
    "RestoreSubscriptions",
    "BotStarted",
    "CommandCompleted",
    "CommandFailed",
    "CommandInvoked",
    "SubscriptionRestored",
]
