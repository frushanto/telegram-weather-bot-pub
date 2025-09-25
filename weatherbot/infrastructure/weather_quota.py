import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from ..core.exceptions import StorageError

logger = logging.getLogger(__name__)


ALERT_THRESHOLDS: Tuple[float, ...] = (0.8, 0.9, 1.0)


@dataclass
class WeatherQuotaStatus:

    limit: int
    used: int
    remaining: int
    reset_at: Optional[datetime]
    ratio: float
    pending_alert_thresholds: Tuple[float, ...]


class WeatherApiQuotaManager:

    def __init__(
        self,
        storage_path: str = "data/weather_api_quota.json",
        max_requests_per_day: int = 1000,
    ) -> None:

        self._storage_path = Path(storage_path)
        self._max_requests_per_day = max_requests_per_day
        self._lock = asyncio.Lock()
        self._timestamps: list[datetime] = []
        self._loaded = False
        self._alert_state_reset_at: Optional[datetime] = None
        self._max_notified_threshold: float = 0.0

    async def try_consume(self, now: Optional[datetime] = None) -> Optional[datetime]:

        if now is None:
            now = datetime.now(timezone.utc)

        await self._ensure_loaded()

        async with self._lock:
            purged = self._purge_expired_locked(now)

            if len(self._timestamps) >= self._max_requests_per_day:
                if purged:
                    await self._save_locked()
                oldest = self._timestamps[0]
                reset_at = oldest + timedelta(hours=24)
                logger.info(
                    "Weather API quota exceeded: %s requests within 24h. Next reset at %s",
                    len(self._timestamps),
                    reset_at.isoformat(),
                )
                return reset_at

            self._timestamps.append(now)
            self._timestamps.sort()
            await self._save_locked()
            return None

    async def get_remaining_quota(self, now: Optional[datetime] = None) -> int:

        status = await self.get_status(now=now)
        return status.remaining

    async def get_status(self, now: Optional[datetime] = None) -> WeatherQuotaStatus:

        if now is None:
            now = datetime.now(timezone.utc)

        await self._ensure_loaded()

        async with self._lock:
            purged = self._purge_expired_locked(now)
            if purged:
                await self._save_locked()

            used = len(self._timestamps)
            remaining = max(self._max_requests_per_day - used, 0)
            reset_at = (
                self._timestamps[0] + timedelta(hours=24) if self._timestamps else None
            )
            ratio = (
                used / self._max_requests_per_day
                if self._max_requests_per_day > 0
                else 0.0
            )

            if self._alert_state_reset_at != reset_at:
                self._alert_state_reset_at = reset_at
                self._max_notified_threshold = 0.0

            pending: Tuple[float, ...] = tuple(
                threshold
                for threshold in ALERT_THRESHOLDS
                if ratio >= threshold and threshold > self._max_notified_threshold
            )

            return WeatherQuotaStatus(
                limit=self._max_requests_per_day,
                used=used,
                remaining=remaining,
                reset_at=reset_at,
                ratio=ratio,
                pending_alert_thresholds=pending,
            )

    async def mark_alert_sent(
        self, threshold: float, reset_at: Optional[datetime]
    ) -> None:

        await self._ensure_loaded()

        async with self._lock:
            if self._alert_state_reset_at != reset_at:
                self._alert_state_reset_at = reset_at
                self._max_notified_threshold = threshold
            elif threshold > self._max_notified_threshold:
                self._max_notified_threshold = threshold

    async def _ensure_loaded(self) -> None:

        if self._loaded:
            return

        async with self._lock:
            if self._loaded:
                return
            try:
                if not self._storage_path.exists():
                    self._timestamps = []
                else:
                    with self._storage_path.open("r", encoding="utf-8") as f:
                        raw = json.load(f)
                    self._timestamps = []
                    if isinstance(raw, list):
                        for value in raw:
                            try:
                                ts = datetime.fromisoformat(value)
                                if ts.tzinfo is None:
                                    ts = ts.replace(tzinfo=timezone.utc)
                                self._timestamps.append(ts.astimezone(timezone.utc))
                            except Exception:
                                logger.warning(
                                    "Skipping invalid timestamp in quota storage: %s",
                                    value,
                                )
                        self._timestamps.sort()
                    else:
                        logger.warning(
                            "Quota storage at %s did not contain a list. Resetting.",
                            self._storage_path,
                        )
                        self._timestamps = []
            except FileNotFoundError:
                self._timestamps = []
            except json.JSONDecodeError:
                logger.warning(
                    "Quota storage at %s corrupted. Resetting storage.",
                    self._storage_path,
                )
                self._timestamps = []
            except Exception as e:
                logger.exception("Failed to load weather quota storage")
                raise StorageError(f"Could not load weather quota storage: {e}")
            self._loaded = True

    def _purge_expired_locked(self, now: datetime) -> bool:

        threshold = now - timedelta(hours=24)
        original_len = len(self._timestamps)
        self._timestamps = [ts for ts in self._timestamps if ts > threshold]
        return len(self._timestamps) != original_len

    async def _save_locked(self) -> None:

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._storage_path.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(
                    [ts.isoformat() for ts in self._timestamps],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            tmp_path.replace(self._storage_path)
        except Exception as e:
            logger.exception("Failed to save weather quota storage")
            raise StorageError(f"Could not save weather quota storage: {e}")

    async def reset(self) -> None:

        await self._ensure_loaded()
        async with self._lock:
            self._timestamps = []
            self._max_notified_threshold = 0.0
            self._alert_state_reset_at = None
            await self._save_locked()
