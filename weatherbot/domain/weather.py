from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class WeatherCurrent:
    temperature: Optional[float]
    apparent_temperature: Optional[float]
    wind_speed: Optional[float]
    weather_code: Optional[int]


@dataclass(frozen=True)
class WeatherDaily:
    min_temperature: Optional[float]
    max_temperature: Optional[float]
    precipitation_probability: Optional[float]
    sunrise: Optional[str]
    sunset: Optional[str]
    wind_speed_max: Optional[float]
    weather_code: Optional[int]


@dataclass(frozen=True)
class WeatherReport:
    current: WeatherCurrent
    daily: List[WeatherDaily] = field(default_factory=list)
    source: str = "open-meteo"
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **updates: Any) -> "WeatherReport":
        merged = dict(self.metadata)
        merged.update(updates)
        return WeatherReport(
            current=self.current,
            daily=list(self.daily),
            source=self.source,
            metadata=merged,
        )

    def day(self, index: int) -> Optional[WeatherDaily]:
        if 0 <= index < len(self.daily):
            return self.daily[index]
        return None

    @classmethod
    def from_open_meteo(cls, payload: dict[str, Any]) -> "WeatherReport":
        current_raw = payload.get("current", {})
        current = WeatherCurrent(
            temperature=_safe_float(current_raw.get("temperature_2m")),
            apparent_temperature=_safe_float(current_raw.get("apparent_temperature")),
            wind_speed=_safe_float(current_raw.get("wind_speed_10m")),
            weather_code=_safe_int(current_raw.get("weather_code")),
        )

        daily_raw = payload.get("daily", {})
        # Open Meteo returns lists for each field; zip them defensively.
        min_temps = _ensure_list(daily_raw.get("temperature_2m_min"))
        max_temps = _ensure_list(daily_raw.get("temperature_2m_max"))
        precipitation = _ensure_list(daily_raw.get("precipitation_probability_max"))
        sunrise = _ensure_list(daily_raw.get("sunrise"))
        sunset = _ensure_list(daily_raw.get("sunset"))
        wind_max = _ensure_list(daily_raw.get("wind_speed_10m_max"))
        weather_codes = _ensure_list(daily_raw.get("weather_code"))

        max_len = (
            max(
                len(seq)
                for seq in (
                    min_temps,
                    max_temps,
                    precipitation,
                    sunrise,
                    sunset,
                    wind_max,
                    weather_codes,
                )
            )
            if daily_raw
            else 0
        )

        daily: List[WeatherDaily] = []
        for idx in range(max_len):
            daily.append(
                WeatherDaily(
                    min_temperature=_safe_float(_get_index(min_temps, idx)),
                    max_temperature=_safe_float(_get_index(max_temps, idx)),
                    precipitation_probability=_safe_float(
                        _get_index(precipitation, idx)
                    ),
                    sunrise=_safe_str(_get_index(sunrise, idx)),
                    sunset=_safe_str(_get_index(sunset, idx)),
                    wind_speed_max=_safe_float(_get_index(wind_max, idx)),
                    weather_code=_safe_int(_get_index(weather_codes, idx)),
                )
            )

        meta = {
            key: value
            for key, value in payload.items()
            if key not in {"current", "daily"}
        }

        return cls(current=current, daily=daily, metadata=meta)


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _get_index(seq: Iterable[Any], index: int) -> Any:
    if isinstance(seq, list):
        if 0 <= index < len(seq):
            return seq[index]
        return None
    if isinstance(seq, tuple):
        if 0 <= index < len(seq):
            return seq[index]
        return None
    try:
        return list(seq)[index]
    except Exception:
        return None


def _safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)
