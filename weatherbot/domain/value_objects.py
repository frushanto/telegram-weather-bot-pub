from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional


@dataclass
class UserHome:
    lat: float
    lon: float
    label: str
    timezone: Optional[str] = None

    STORAGE_KEYS = ("lat", "lon", "label", "timezone")

    def to_storage(self) -> dict[str, Any]:
        payload = {"lat": self.lat, "lon": self.lon, "label": self.label}
        if self.timezone:
            payload["timezone"] = self.timezone
        return payload

    @classmethod
    def from_storage(cls, data: Mapping[str, Any]) -> Optional["UserHome"]:
        if not all(key in data for key in ("lat", "lon", "label")):
            return None
        try:
            lat = float(data["lat"])
            lon = float(data["lon"])
        except (TypeError, ValueError):
            return None
        label = str(data["label"]).strip()
        if not label:
            return None
        timezone = data.get("timezone")
        if timezone is not None:
            timezone = str(timezone)
        return cls(lat=lat, lon=lon, label=label, timezone=timezone)

    def with_timezone(self, timezone: Optional[str]) -> "UserHome":
        return replace(self, timezone=timezone)


@dataclass
class UserSubscription:
    hour: int
    minute: int = 0

    STORAGE_KEYS = ("sub_hour", "sub_min")

    def to_storage(self) -> dict[str, Any]:
        return {"sub_hour": self.hour, "sub_min": self.minute}

    @classmethod
    def from_storage(cls, data: Mapping[str, Any]) -> Optional["UserSubscription"]:
        raw_hour = data.get("sub_hour")
        if raw_hour is None:
            return None
        try:
            hour = int(raw_hour)
        except (TypeError, ValueError):
            return None
        if not (0 <= hour <= 23):
            return None
        raw_minute = data.get("sub_min", 0)
        try:
            minute = int(raw_minute)
        except (TypeError, ValueError):
            minute = 0
        if not (0 <= minute <= 59):
            minute = 0
        return cls(hour=hour, minute=minute)


@dataclass
class UserProfile:
    language: str = "ru"
    language_explicit: bool = False
    home: Optional[UserHome] = None
    subscription: Optional[UserSubscription] = None
    extras: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.extras is None:
            self.extras = {}

    def to_storage(self) -> dict[str, Any]:
        data = dict(self.extras)
        if self.language and (
            self.language_explicit or self.language not in {"", "ru"}
        ):
            data["language"] = self.language
        else:
            data.pop("language", None)
        if self.home:
            data.update(self.home.to_storage())
        else:
            for key in UserHome.STORAGE_KEYS:
                data.pop(key, None)
        if self.subscription:
            data.update(self.subscription.to_storage())
        else:
            for key in UserSubscription.STORAGE_KEYS:
                data.pop(key, None)
        return data

    def is_empty(self) -> bool:
        return (
            self.home is None
            and self.subscription is None
            and not self.extras
            and (self.language == "ru" or not self.language)
        )

    @classmethod
    def from_storage(cls, data: Mapping[str, Any]) -> "UserProfile":
        raw = dict(data)
        language = str(raw.get("language", "ru") or "ru")
        language_explicit = "language" in raw
        home = UserHome.from_storage(raw)
        subscription = UserSubscription.from_storage(raw)
        known_keys = (
            set(UserHome.STORAGE_KEYS)
            | set(UserSubscription.STORAGE_KEYS)
            | {"language"}
        )
        extras = {k: v for k, v in raw.items() if k not in known_keys}
        return cls(
            language=language,
            language_explicit=language_explicit,
            home=home,
            subscription=subscription,
            extras=extras,
        )


@dataclass
class SubscriptionEntry:
    chat_id: str
    subscription: UserSubscription
    home: Optional[UserHome]
    language: Optional[str] = None
