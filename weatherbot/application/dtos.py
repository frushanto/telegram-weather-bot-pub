"""Data transfer object definitions for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, TypeAlias, TypedDict

from weatherbot.domain.value_objects import UserHome, UserProfile, UserSubscription
from weatherbot.domain.weather import WeatherReport


class SubscriptionScheduleDTO(TypedDict):
    """Represents a normalized subscription schedule for a chat."""

    hour: int
    minute: int


SubscriptionScheduleMap: TypeAlias = dict[str, SubscriptionScheduleDTO]
"""Mapping between chat identifiers and their subscription schedule."""


@dataclass(frozen=True, slots=True)
class UserDataDTO:
    """Snapshot of user-related settings maintained by the bot."""

    language: str
    language_explicit: bool
    home: Optional[UserHome]
    subscription: Optional[UserSubscription]
    extras: Mapping[str, Any]

    @classmethod
    def from_profile(cls, profile: UserProfile) -> "UserDataDTO":
        """Create a snapshot from a :class:`~weatherbot.domain.value_objects.UserProfile`."""

        return cls(
            language=profile.language,
            language_explicit=profile.language_explicit,
            home=profile.home,
            subscription=profile.subscription,
            extras=dict(profile.extras),
        )

    def to_profile(self) -> UserProfile:
        """Convert the snapshot back to a :class:`UserProfile`."""

        return UserProfile(
            language=self.language,
            language_explicit=self.language_explicit,
            home=self.home,
            subscription=self.subscription,
            extras=dict(self.extras),
        )

    def to_storage(self) -> dict[str, Any]:
        """Render the snapshot into a serializable dictionary."""

        return self.to_profile().to_storage()


@dataclass(frozen=True, slots=True)
class GeocodeResultDTO:
    """Normalized geocoding result returned by the application service."""

    lat: float
    lon: float
    label: str


@dataclass(frozen=True, slots=True)
class CityWeatherDTO:
    """Weather information resolved for a specific city label."""

    report: WeatherReport
    location: GeocodeResultDTO


__all__ = [
    "SubscriptionScheduleDTO",
    "SubscriptionScheduleMap",
    "UserDataDTO",
    "GeocodeResultDTO",
    "CityWeatherDTO",
]
