from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def format_reset_time(reset_at: datetime, tz_name: Optional[str] = None) -> str:
    """Format reset time in a readable form, using the provided timezone if possible."""

    if tz_name:
        try:
            zone = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            # Fallback to UTC formatting when timezone is invalid or unsupported.
            return reset_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        else:
            localized = reset_at.astimezone(zone)
            return localized.strftime("%Y-%m-%d %H:%M %Z")

    return reset_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
