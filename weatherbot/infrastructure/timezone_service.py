import datetime
import logging
from typing import Optional

import pytz
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class TimezoneService:
    """Service for timezone operations based on geographical coordinates."""

    def __init__(self):
        self._tf = TimezoneFinder()

    def get_timezone_by_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """
        Get timezone name by latitude and longitude coordinates.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            Timezone name (e.g., 'Europe/Moscow') or None if not found
        """
        try:
            timezone_name = self._tf.timezone_at(lat=lat, lng=lon)
            if timezone_name:
                # Validate that the timezone exists in pytz
                try:
                    pytz.timezone(timezone_name)
                    logger.debug(
                        f"Found timezone '{timezone_name}' for coordinates {lat:.4f}, {lon:.4f}"
                    )
                    return timezone_name
                except pytz.UnknownTimeZoneError:
                    logger.warning(
                        f"Unknown timezone '{timezone_name}' for coordinates {lat:.4f}, {lon:.4f}"
                    )
                    return None
            else:
                logger.warning(
                    f"No timezone found for coordinates {lat:.4f}, {lon:.4f}"
                )
                return None
        except Exception as e:
            logger.exception(
                f"Error getting timezone for coordinates {lat:.4f}, {lon:.4f}: {e}"
            )
            return None

    def validate_timezone(self, timezone_name: str) -> bool:
        """
        Validate that timezone name exists in pytz.

        Args:
            timezone_name: Timezone name to validate

        Returns:
            True if timezone is valid, False otherwise
        """
        try:
            pytz.timezone(timezone_name)
            return True
        except pytz.UnknownTimeZoneError:
            return False

    def get_timezone_info(self, timezone_name: str) -> Optional[dict]:
        """
        Get timezone information including UTC offset.

        Args:
            timezone_name: Timezone name

        Returns:
            Dict with timezone info or None if invalid timezone
        """
        try:
            if not self.validate_timezone(timezone_name):
                return None

            tz = pytz.timezone(timezone_name)
            now = pytz.utc.localize(datetime.datetime.utcnow())
            local_time = now.astimezone(tz)

            return {
                "timezone": timezone_name,
                "utc_offset": local_time.utcoffset().total_seconds() / 3600,  # hours
                "dst_active": bool(local_time.dst()),
                "abbreviation": local_time.strftime("%Z"),
            }
        except Exception as e:
            logger.exception(f"Error getting timezone info for '{timezone_name}': {e}")
            return None

    @staticmethod
    def get_common_timezones() -> list:
        """Get list of common timezone names."""
        return list(pytz.common_timezones)
