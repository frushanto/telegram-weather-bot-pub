import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from weatherbot.core.config import BotConfig, SpamConfig, set_config
from weatherbot.jobs.backup import _cleanup_old_backups, perform_backup  # type: ignore


@pytest.mark.asyncio
async def test_backup_creation_and_retention(tmp_path):
    # Prepare storage file
    storage_dir = tmp_path / "data"
    storage_dir.mkdir()
    storage_file = storage_dir / "storage.json"
    storage_file.write_text(json.dumps({"u": {"lang": "ru"}}), encoding="utf-8")

    # Configure bot with custom storage path & short retention
    cfg = BotConfig(
        token="t",
        admin_ids=[],
        admin_language="ru",
        spam_config=SpamConfig(),
        storage_path=str(storage_file),
        backup_enabled=True,
        backup_retention_days=1,
        backup_time_hour=3,
    )
    set_config(cfg)

    # Run backup
    await perform_backup()

    backups_dir = storage_dir / "backups"
    assert backups_dir.exists()
    backups = list(backups_dir.glob("storage-*.json"))
    assert len(backups) == 1

    # Create old backup (simulate > retention)
    old_backup = backups_dir / "storage-20000101-000000.json"
    old_backup.write_text("{}", encoding="utf-8")
    assert old_backup.exists()

    # Force cleanup
    await _cleanup_old_backups(backups_dir, days=1)

    remaining = list(backups_dir.glob("storage-*.json"))
    # New backup should remain, old should be pruned
    assert any(b.name != old_backup.name for b in remaining)
    assert not any(b.name == old_backup.name for b in remaining)
