import json
from datetime import datetime, timedelta, timezone

import pytest

from weatherbot.infrastructure.weather_quota import WeatherApiQuotaManager


@pytest.mark.asyncio
async def test_quota_enforces_limit(tmp_path):

    storage_path = tmp_path / "quota.json"
    manager = WeatherApiQuotaManager(
        storage_path=str(storage_path), max_requests_per_day=3
    )

    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert await manager.try_consume(now=base_time) is None
    assert await manager.try_consume(now=base_time + timedelta(hours=1)) is None
    assert await manager.try_consume(now=base_time + timedelta(hours=2)) is None

    reset_at = await manager.try_consume(now=base_time + timedelta(hours=3))
    assert reset_at == base_time + timedelta(hours=24)


@pytest.mark.asyncio
async def test_quota_prunes_old_entries(tmp_path):

    storage_path = tmp_path / "quota.json"
    manager = WeatherApiQuotaManager(
        storage_path=str(storage_path), max_requests_per_day=2
    )

    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    await manager.try_consume(now=base_time)
    await manager.try_consume(now=base_time + timedelta(hours=1))

    reset_at = await manager.try_consume(now=base_time + timedelta(hours=2))
    assert reset_at == base_time + timedelta(hours=24)

    # After 24 hours the earliest request should expire
    assert await manager.try_consume(now=base_time + timedelta(hours=25)) is None

    remaining = await manager.get_remaining_quota(now=base_time + timedelta(hours=25))
    assert remaining == 1


@pytest.mark.asyncio
async def test_quota_status_thresholds(tmp_path):

    storage_path = tmp_path / "quota.json"
    manager = WeatherApiQuotaManager(
        storage_path=str(storage_path), max_requests_per_day=5
    )

    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    for offset in range(4):
        await manager.try_consume(now=base_time + timedelta(hours=offset))

    status = await manager.get_status(now=base_time + timedelta(hours=4))
    assert status.used == 4
    assert status.remaining == 1
    assert status.pending_alert_thresholds == (0.8,)

    await manager.mark_alert_sent(0.8, status.reset_at)

    status_after = await manager.get_status(now=base_time + timedelta(hours=5))
    assert status_after.pending_alert_thresholds == ()

    # Consume the last allowed request
    await manager.try_consume(now=base_time + timedelta(hours=5))
    status_full = await manager.get_status(
        now=base_time + timedelta(hours=5, minutes=1)
    )
    assert status_full.used == 5
    assert status_full.pending_alert_thresholds == (0.9, 1.0)

    await manager.mark_alert_sent(1.0, status_full.reset_at)
    cleared_status = await manager.get_status(
        now=base_time + timedelta(hours=5, minutes=2)
    )
    assert cleared_status.pending_alert_thresholds == ()


@pytest.mark.asyncio
async def test_quota_storage_persistence(tmp_path):

    storage_path = tmp_path / "quota.json"
    manager = WeatherApiQuotaManager(
        storage_path=str(storage_path), max_requests_per_day=4
    )

    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    await manager.try_consume(now=base_time)

    assert storage_path.exists()
    first_dump = json.loads(storage_path.read_text(encoding="utf-8"))
    assert first_dump == [base_time.isoformat()]

    # Force prune of expired entries after 24h window
    await manager.get_status(now=base_time + timedelta(hours=25))
    second_dump = json.loads(storage_path.read_text(encoding="utf-8"))
    assert second_dump == []

    await manager.try_consume(now=base_time + timedelta(hours=25))
    third_dump = json.loads(storage_path.read_text(encoding="utf-8"))
    assert len(third_dump) == 1

    await manager.reset()
    reset_dump = json.loads(storage_path.read_text(encoding="utf-8"))
    assert reset_dump == []
