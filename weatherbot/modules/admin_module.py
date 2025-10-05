"""Module configuring administrative commands."""

from __future__ import annotations

from dataclasses import dataclass

from telegram.ext import CommandHandler

from ..application.interfaces import AdminApplicationServiceProtocol
from ..handlers import admin_commands
from ..handlers.admin_commands import (
    AdminHandlerDependencies,
    configure_admin_handlers,
)
from ..presentation.i18n import Localization
from .base import Module, ModuleContext
from .requests import GetAdminCommandMap


@dataclass
class AdminModule(Module):
    name: str = "admin"
    order: int = 10

    def setup(self, context: ModuleContext) -> None:  # noqa: D401
        mediator = context.mediator
        config = context.config
        container = context.container

        configure_admin_handlers(
            AdminHandlerDependencies(
                admin_service=container.get(AdminApplicationServiceProtocol),
                localization=container.get(Localization),
                config_provider=lambda: config,
            )
        )

        def _resolve(_: GetAdminCommandMap):
            if not config.admin_ids:
                return {}

            # Build a map of command names to handlers for configured admins only.
            return {
                "admin_stats": admin_commands.admin_stats_cmd,
                "admin_unblock": admin_commands.admin_unblock_cmd,
                "admin_user_info": admin_commands.admin_user_info_cmd,
                "admin_cleanup": admin_commands.admin_cleanup_cmd,
                "admin_subscriptions": admin_commands.admin_subscriptions_cmd,
                "admin_backup": admin_commands.admin_backup_now_cmd,
                "admin_config": admin_commands.admin_config_cmd,
                "admin_test_weather": admin_commands.admin_test_weather_cmd,
                "admin_quota": admin_commands.admin_quota_cmd,
                "admin_help": admin_commands.admin_help_cmd,
                "admin_version": admin_commands.admin_version_cmd,
            }

        mediator.register(GetAdminCommandMap, _resolve)

        if not config.admin_ids:
            return

        admin_map = mediator.send_sync(GetAdminCommandMap())
        for name, handler in admin_map.items():
            context.application.add_handler(CommandHandler(name, handler))
