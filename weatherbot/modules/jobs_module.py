"""Module responsible for scheduling recurring jobs."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from telegram.ext import CallbackContext

from ..application.dtos import SubscriptionScheduleDTO
from ..application.interfaces import SubscriptionServiceProtocol
from ..domain.services import SpamProtectionService
from ..jobs.backup import schedule_daily_backup
from ..jobs.scheduler import schedule_daily_timezone_aware
from .base import Module, ModuleContext
from .events import SubscriptionRestored
from .requests import RestoreSubscriptions


@dataclass
class JobsModule(Module):
    name: str = "jobs"
    order: int = 30

    def setup(self, context: ModuleContext) -> None:  # noqa: D401
        mediator = context.mediator
        event_bus = context.event_bus
        tracer = context.tracer
        metrics = context.metrics

        container = context.container
        subscription_service = container.get(SubscriptionServiceProtocol)
        spam_service = container.get(SpamProtectionService)

        async def _restore_subscriptions(request: RestoreSubscriptions) -> None:
            schedules = await subscription_service.get_all_subscriptions_dict()
            metrics.active_subscriptions.set(0)
            # Re-register every persisted subscription in the Telegram job queue.
            for chat_id, schedule in schedules.items():
                dto: SubscriptionScheduleDTO = schedule
                with tracer.span("jobs.restore_subscription", chat_id=chat_id):
                    await schedule_daily_timezone_aware(
                        request.application.job_queue,
                        int(chat_id),
                        dto["hour"],
                        dto["minute"],
                    )
                    metrics.active_subscriptions.inc()
                    await event_bus.publish(SubscriptionRestored(chat_id=int(chat_id)))

        mediator.register(RestoreSubscriptions, _restore_subscriptions)

        async def _cleanup_spam(context: CallbackContext) -> None:
            await spam_service.cleanup_old_data()

        job_queue = context.application.job_queue
        job_queue.run_daily(
            _cleanup_spam,
            name="cleanup_spam_data",
            time=datetime.time(hour=2, minute=0, tzinfo=context.config.timezone),
        )

        schedule_daily_backup(job_queue)

        async def _startup() -> None:
            await mediator.send(RestoreSubscriptions(context.application))

        context.on_startup(_startup)

        context.health.register("job_queue", lambda: job_queue is not None)
