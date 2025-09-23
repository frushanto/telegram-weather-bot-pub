from typing import Optional

from weatherbot.presentation.i18n import i18n
from weatherbot.utils.wmo import wmo_to_text


def format_weather(
    data: dict, place_label: Optional[str] = None, lang: str = "ru"
) -> str:
    cur = data.get("current", {})
    daily = data.get("daily", {})

    t = cur.get("temperature_2m")
    t_feel = cur.get("apparent_temperature")
    wind = cur.get("wind_speed_10m")
    code = cur.get("weather_code")

    t_max = (daily.get("temperature_2m_max") or [None])[0]
    t_min = (daily.get("temperature_2m_min") or [None])[0]
    p_max = (daily.get("precipitation_probability_max") or [None])[0]
    sunrise = (daily.get("sunrise") or ["—"])[0]
    sunset = (daily.get("sunset") or ["—"])[0]

    t_max_tomorrow = (
        (daily.get("temperature_2m_max") or [None, None])[1]
        if len(daily.get("temperature_2m_max", [])) > 1
        else None
    )
    t_min_tomorrow = (
        (daily.get("temperature_2m_min") or [None, None])[1]
        if len(daily.get("temperature_2m_min", [])) > 1
        else None
    )
    p_max_tomorrow = (
        (daily.get("precipitation_probability_max") or [None, None])[1]
        if len(daily.get("precipitation_probability_max", [])) > 1
        else None
    )
    wind_max_tomorrow = (
        (daily.get("wind_speed_10m_max") or [None, None])[1]
        if len(daily.get("wind_speed_10m_max", [])) > 1
        else None
    )
    weather_code_tomorrow = (
        (daily.get("weather_code") or [None, None])[1]
        if len(daily.get("weather_code", [])) > 1
        else None
    )

    t_max_day_after = (
        (daily.get("temperature_2m_max") or [None, None, None])[2]
        if len(daily.get("temperature_2m_max", [])) > 2
        else None
    )
    t_min_day_after = (
        (daily.get("temperature_2m_min") or [None, None, None])[2]
        if len(daily.get("temperature_2m_min", [])) > 2
        else None
    )
    p_max_day_after = (
        (daily.get("precipitation_probability_max") or [None, None, None])[2]
        if len(daily.get("precipitation_probability_max", [])) > 2
        else None
    )
    wind_max_day_after = (
        (daily.get("wind_speed_10m_max") or [None, None, None])[2]
        if len(daily.get("wind_speed_10m_max", [])) > 2
        else None
    )
    weather_code_day_after = (
        (daily.get("weather_code") or [None, None, None])[2]
        if len(daily.get("weather_code", [])) > 2
        else None
    )

    def format_time(time_str):
        if time_str == "—" or time_str is None:
            return "—"

        if "T" in str(time_str):
            time_part = str(time_str).split("T")[1]

            return time_part[:5]
        return str(time_str)

    sunrise_formatted = format_time(sunrise)
    sunset_formatted = format_time(sunset)

    loc = f"📍 {place_label}\n\n" if place_label else ""
    desc = wmo_to_text(code, lang)

    temp_line = f"🌡 {i18n.get('temperature', lang)}: <b>{t}°C</b>"
    if t_feel is not None:
        temp_line += f" ({i18n.get('feels_like', lang)} <b>{t_feel}°C</b>)"

    lines = [
        f"{loc}{i18n.get('weather_now', lang)}: {desc}",
        temp_line,
        f"💨 {i18n.get('wind', lang)}: <b>{wind} {i18n.get('wind_unit', lang)}</b>",
        "",
        f"{i18n.get('today', lang)}:",
        f"↘️ {i18n.get('min_temp', lang)}: <b>{t_min}°C</b>   ↗️ {i18n.get('max_temp', lang)}: <b>{t_max}°C</b>",
        f"☔ {i18n.get('precipitation_max', lang)}: <b>{p_max}%</b>",
        f"🌅 {i18n.get('sunrise', lang)}: {sunrise_formatted}",
        f"🌇 {i18n.get('sunset', lang)}: {sunset_formatted}",
    ]

    if any(
        [
            t_max_tomorrow is not None,
            t_min_tomorrow is not None,
            p_max_tomorrow is not None,
            wind_max_tomorrow is not None,
        ]
    ):

        if weather_code_tomorrow is not None:
            tomorrow_desc = wmo_to_text(weather_code_tomorrow, lang)
            tomorrow_header = f"{i18n.get('tomorrow', lang)} ({tomorrow_desc}):"
        else:
            tomorrow_header = f"{i18n.get('tomorrow', lang)}:"

        t_min_formatted = (
            f"<b>{t_min_tomorrow}°C</b>" if t_min_tomorrow is not None else "<b>—°C</b>"
        )
        t_max_formatted = (
            f"<b>{t_max_tomorrow}°C</b>" if t_max_tomorrow is not None else "<b>—°C</b>"
        )
        p_formatted = (
            f"<b>{p_max_tomorrow}%</b>" if p_max_tomorrow is not None else "<b>—%</b>"
        )

        forecast_line = f"🌡 {t_min_formatted} ... {t_max_formatted}   ☔ {p_formatted}"
        if wind_max_tomorrow is not None:
            forecast_line += (
                f"   💨 <b>{wind_max_tomorrow} {i18n.get('wind_unit', lang)}</b>"
            )
        lines.extend(["", tomorrow_header, forecast_line])

    if any(
        [
            t_max_day_after is not None,
            t_min_day_after is not None,
            p_max_day_after is not None,
            wind_max_day_after is not None,
        ]
    ):

        if weather_code_day_after is not None:
            day_after_desc = wmo_to_text(weather_code_day_after, lang)
            day_after_header = (
                f"{i18n.get('day_after_tomorrow', lang)} ({day_after_desc}):"
            )
        else:
            day_after_header = f"{i18n.get('day_after_tomorrow', lang)}:"

        t_min_formatted_da = (
            f"<b>{t_min_day_after}°C</b>"
            if t_min_day_after is not None
            else "<b>—°C</b>"
        )
        t_max_formatted_da = (
            f"<b>{t_max_day_after}°C</b>"
            if t_max_day_after is not None
            else "<b>—°C</b>"
        )
        p_formatted_da = (
            f"<b>{p_max_day_after}%</b>" if p_max_day_after is not None else "<b>—%</b>"
        )

        forecast_line_da = (
            f"🌡 {t_min_formatted_da} ... {t_max_formatted_da}   ☔ {p_formatted_da}"
        )
        if wind_max_day_after is not None:
            forecast_line_da += (
                f"   💨 <b>{wind_max_day_after} {i18n.get('wind_unit', lang)}</b>"
            )
        lines.extend(["", day_after_header, forecast_line_da])
    return "\n".join(lines)
