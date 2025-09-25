from __future__ import annotations

from typing import Optional, Union

from weatherbot.domain.weather import WeatherDaily, WeatherReport
from weatherbot.presentation.i18n import i18n
from weatherbot.utils.wmo import wmo_to_text


def format_weather(
    data: Union[WeatherReport, dict],
    place_label: Optional[str] = None,
    lang: str = "ru",
) -> str:
    """Render weather information using rich domain objects."""

    report = (
        data if isinstance(data, WeatherReport) else WeatherReport.from_open_meteo(data)
    )

    current = report.current
    today = report.day(0) or WeatherDaily(
        min_temperature=None,
        max_temperature=None,
        precipitation_probability=None,
        sunrise=None,
        sunset=None,
        wind_speed_max=None,
        weather_code=None,
    )
    tomorrow = report.day(1)
    day_after = report.day(2)

    loc = f"📍 {place_label}\n\n" if place_label else ""
    desc = wmo_to_text(current.weather_code, lang)

    temp_line = _format_temperature_line(current, lang)
    wind_line = f"💨 {i18n.get('wind', lang)}: <b>{_fmt_value(current.wind_speed)} {i18n.get('wind_unit', lang)}</b>"

    lines = [
        f"{loc}{i18n.get('weather_now', lang)}: {desc}",
        temp_line,
        wind_line,
        "",
    ]

    lines.extend(_format_today_section(today, lang))

    if tomorrow and _has_forecast_data(tomorrow):
        lines.extend(_format_future_section(tomorrow, lang, i18n.get("tomorrow", lang)))

    if day_after and _has_forecast_data(day_after):
        title = i18n.get("day_after_tomorrow", lang)
        lines.extend(_format_future_section(day_after, lang, title))

    return "\n".join(line for line in lines if line is not None)


def _format_temperature_line(current, lang: str) -> str:
    base = (
        f"🌡 {i18n.get('temperature', lang)}: <b>{_fmt_value(current.temperature)}°C</b>"
    )
    if current.apparent_temperature is not None:
        base += f" ({i18n.get('feels_like', lang)} <b>{_fmt_value(current.apparent_temperature)}°C</b>)"
    return base


def _format_today_section(day: WeatherDaily, lang: str) -> list[str]:
    sunrise = _format_time(day.sunrise)
    sunset = _format_time(day.sunset)

    return [
        f"{i18n.get('today', lang)}:",
        f"↘️ {i18n.get('min_temp', lang)}: <b>{_fmt_value(day.min_temperature)}°C</b>   "
        f"↗️ {i18n.get('max_temp', lang)}: <b>{_fmt_value(day.max_temperature)}°C</b>",
        f"☔ {i18n.get('precipitation_max', lang)}: <b>{_fmt_value(day.precipitation_probability)}%</b>",
        f"🌅 {i18n.get('sunrise', lang)}: {sunrise}",
        f"🌇 {i18n.get('sunset', lang)}: {sunset}",
    ]


def _format_future_section(day: WeatherDaily, lang: str, title: str) -> list[str]:
    weather_line = _future_header(day, lang, title)
    forecast_line = (
        f"🌡 <b>{_fmt_value(day.min_temperature)}°C</b> ... <b>{_fmt_value(day.max_temperature)}°C</b>   "
        f"☔ <b>{_fmt_value(day.precipitation_probability)}%</b>"
    )
    if day.wind_speed_max is not None:
        forecast_line += f"   💨 <b>{_fmt_value(day.wind_speed_max)} {i18n.get('wind_unit', lang)}</b>"
    return ["", weather_line, forecast_line]


def _future_header(day: WeatherDaily, lang: str, title: str) -> str:
    if day.weather_code is None:
        return f"{title}:"
    desc = wmo_to_text(day.weather_code, lang)
    return f"{title} ({desc}):"


def _fmt_value(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _format_time(value: Optional[str]) -> str:
    if not value:
        return "—"
    if "T" in value:
        return value.split("T", 1)[1][:5]
    return value


def _has_forecast_data(day: WeatherDaily) -> bool:
    return any(
        field is not None
        for field in (
            day.min_temperature,
            day.max_temperature,
            day.precipitation_probability,
            day.wind_speed_max,
        )
    )
