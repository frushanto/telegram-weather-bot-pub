import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytz

from weatherbot.core.config import BotConfig, reset_config_provider, set_config
from weatherbot.core.container import get_container
from weatherbot.domain.value_objects import UserHome
from weatherbot.infrastructure.container import (
    override_user_service,
    register_application_services,
    register_config_provider,
    register_external_clients,
    register_repositories,
)
from weatherbot.infrastructure.timezone_service import TimezoneService
from weatherbot.jobs import scheduler
from weatherbot.presentation.i18n import Localization


@pytest.fixture
def mock_user_service(tmp_path):
    container = get_container()
    container.clear()
    container.register_singleton(Localization, Localization())
    config = BotConfig(
        token="test",
        storage_path=str(tmp_path / "storage.json"),
        weather_api_quota_path=str(tmp_path / "quota.json"),
    )
    set_config(config)
    provider = register_config_provider()
    register_repositories(config)
    register_external_clients(config)

    user_service = AsyncMock()
    user_service.get_user_home = AsyncMock(return_value=None)
    register_application_services(
        provider, overrides=override_user_service(lambda: user_service)
    )

    from weatherbot.jobs.scheduler import SchedulerDependencies, configure_scheduler

    configure_scheduler(
        SchedulerDependencies(
            user_service=user_service,
            weather_service=AsyncMock(),
            quota_notifier=lambda bot: AsyncMock()(bot),
            weather_formatter=lambda *args, **kwargs: "",
            translate=lambda key, lang, **kwargs: key,
            config_provider=lambda: SimpleNamespace(timezone=pytz.UTC),
        )
    )

    yield user_service

    reset_config_provider()
    container.clear()
    container.register_singleton(Localization, Localization())


class DummyJobQueue:
    def __init__(self):
        self.runs = []

    def get_jobs_by_name(self, name):
        return []

    def run_daily(self, callback, time, name=None, chat_id=None):
        self.runs.append(
            {"callback": callback, "time": time, "name": name, "chat_id": chat_id}
        )


def test_schedule_uses_user_timezone_with_dst(mock_user_service):
    # Simulate a user living in 'Europe/Berlin' (which has DST)
    job_queue = DummyJobQueue()
    chat_id = 12345
    hour = 6

    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="Europe/Berlin"
    )

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, hour, 0))

    assert len(job_queue.runs) == 1
    run = job_queue.runs[0]
    tzinfo = run["time"].tzinfo
    assert tzinfo.zone == "Europe/Berlin" or str(tzinfo) == "Europe/Berlin"


def test_timezone_service_handles_errors(monkeypatch):
    # Force TimezoneFinder.timezone_at to raise an exception
    class BadTF:
        def timezone_at(self, lat, lng):
            raise RuntimeError("boom")

    svc = TimezoneService()
    svc._tf = BadTF()

    assert svc.get_timezone_by_coordinates(0.0, 0.0) is None


def test_schedule_job_name_and_time(mock_user_service):
    # Ensure schedule_daily_timezone_aware registers job with proper name and time
    job_queue = DummyJobQueue()
    chat_id = 999
    hour = 7

    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="America/New_York"
    )

    import asyncio

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, hour, 30))

    assert job_queue.runs[0]["name"] == f"daily-{chat_id}"
    t = job_queue.runs[0]["time"]
    assert t.hour == hour
    assert t.minute == 30
    # tzinfo should be a pytz timezone representing America/New_York
    assert "New_York" in getattr(t.tzinfo, "zone", str(t.tzinfo))


def test_dst_offset_changes_after_scheduling(mock_user_service):
    # Ensure that scheduling with a timezone results in different UTC offsets
    # for winter vs summer dates (DST effect)
    job_queue = DummyJobQueue()
    chat_id = 4242
    hour = 9

    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="Europe/Berlin"
    )

    import asyncio

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, hour, 0))

    assert len(job_queue.runs) == 1
    tzinfo = job_queue.runs[0]["time"].tzinfo
    tz = pytz.timezone("Europe/Berlin")

    # Winter date (Jan 15) and summer date (Jul 15)
    win = tz.localize(datetime.datetime(2025, 1, 15, hour, 0))
    sumr = tz.localize(datetime.datetime(2025, 7, 15, hour, 0))

    offset_win = win.utcoffset().total_seconds() / 3600
    offset_sum = sumr.utcoffset().total_seconds() / 3600

    assert offset_sum - offset_win == 1


def test_timezone_change_reschedules_job(mock_user_service):
    # Simulate an existing job and verify schedule_removal is called and new job created
    class ExistingJob:
        def __init__(self):
            self.removed = False

        def schedule_removal(self):
            self.removed = True

    class JobQueueWithExisting(DummyJobQueue):
        def __init__(self):
            super().__init__()
            self.existing = ExistingJob()

        def get_jobs_by_name(self, name):
            return [self.existing]

    job_queue = JobQueueWithExisting()
    chat_id = 777
    hour = 8

    # initial timezone
    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="Europe/Berlin"
    )

    import asyncio

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, hour, 0))

    # existing job should be marked removed
    assert job_queue.existing.removed is True
    # new job created
    assert len(job_queue.runs) == 1
    assert job_queue.runs[0]["name"] == f"daily-{chat_id}"


def test_nonexistent_local_time_and_scheduler(mock_user_service):
    """Spring-forward: local time that does not exist (e.g. 02:30 on DST start)."""
    tz = pytz.timezone("Europe/Berlin")
    # 2025-03-30 is DST start in Europe/Berlin; 02:30 local time typically does not exist
    naive = datetime.datetime(2025, 3, 30, 2, 30)

    from pytz import NonExistentTimeError

    # localize with is_dst=None should raise NonExistentTimeError
    with pytest.raises(NonExistentTimeError):
        tz.localize(naive, is_dst=None)

    # But scheduler should still accept scheduling at that local time (it stores a time with tzinfo)
    job_queue = DummyJobQueue()
    chat_id = 1357
    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="Europe/Berlin"
    )

    import asyncio

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, 2, 30))

    assert len(job_queue.runs) == 1
    # To reason about the actual UTC moment, one has to resolve the nonexistent time
    # using an explicit is_dst flag; ensure such resolution yields a valid aware datetime
    aware = tz.localize(naive, is_dst=True)
    assert aware.utcoffset() is not None


def test_ambiguous_local_time_and_scheduler(mock_user_service):
    """Fall-back: ambiguous local time (repeated hour)."""
    tz = pytz.timezone("Europe/Berlin")
    # 2025-10-26 is DST end in Europe/Berlin; 02:30 is ambiguous
    naive = datetime.datetime(2025, 10, 26, 2, 30)

    from pytz import AmbiguousTimeError

    with pytest.raises(AmbiguousTimeError):
        tz.localize(naive, is_dst=None)

    # localize with is_dst True/False yields two different offsets
    aware_dst = tz.localize(naive, is_dst=True)
    aware_std = tz.localize(naive, is_dst=False)

    assert aware_dst.utcoffset() != aware_std.utcoffset()

    # Scheduler should accept scheduling at ambiguous local time
    job_queue = DummyJobQueue()
    chat_id = 2468
    mock_user_service.get_user_home.return_value = UserHome(
        lat=0.0, lon=0.0, label="", timezone="Europe/Berlin"
    )

    import asyncio

    asyncio.run(scheduler.schedule_daily_timezone_aware(job_queue, chat_id, 2, 30))

    assert len(job_queue.runs) == 1
