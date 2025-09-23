import logging
from datetime import datetime, timedelta
from pathlib import Path

from weatherbot.core.config import get_config

logger = logging.getLogger(__name__)


async def perform_backup() -> None:
    config = get_config()
    storage = Path(config.storage_path)
    if not storage.exists():
        logger.warning("Backup skipped: storage file not found (%s)", storage)
        return

    backup_dir = storage.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = backup_dir / f"storage-{timestamp}.json"

    try:
        data = storage.read_bytes()
        backup_file.write_bytes(data)
        logger.info("Created storage backup: %s", backup_file.name)
    except Exception:
        logger.exception("Failed to create storage backup")
        return

    await _cleanup_old_backups(backup_dir, days=config.backup_retention_days)


async def _cleanup_old_backups(backup_dir: Path, days: int) -> None:
    if days <= 0:
        return
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0
    for f in backup_dir.glob("storage-*.json"):
        try:

            stem = f.stem
            ts_part = stem.replace("storage-", "")
            dt = datetime.strptime(ts_part, "%Y%m%d-%H%M%S")
            if dt < cutoff:
                f.unlink(missing_ok=True)
                deleted += 1
        except Exception:
            logger.warning("Skipping unexpected backup file name: %s", f.name)
    if deleted:
        logger.info("Deleted %d old backup(s) (retention %d days)", deleted, days)


def schedule_daily_backup(job_queue) -> None:
    config = get_config()
    if not config.backup_enabled:
        logger.info("Storage backup disabled (BACKUP_ENABLED=false)")
        return

    from datetime import time as dtime

    job_queue.run_daily(
        _backup_job_wrapper,
        time=dtime(hour=config.backup_time_hour, minute=5, tzinfo=config.timezone),
        name="storage_backup",
    )
    logger.info(
        "Scheduled storage backup daily at %02d:05 (retention %d days)",
        config.backup_time_hour,
        config.backup_retention_days,
    )


async def _backup_job_wrapper(context):
    try:
        await perform_backup()
    except Exception:
        logger.exception("Unexpected error during storage backup job")
