from weatherbot.presentation import formatter


def test_format_weather_simple():
    data = {
        "current": {
            "temperature_2m": 20,
            "apparent_temperature": 18,
            "wind_speed_10m": 5,
            "weather_code": 0,
        },
        "daily": {
            "temperature_2m_max": [22],
            "temperature_2m_min": [15],
            "precipitation_probability_max": [10],
            "sunrise": ["06:00"],
            "sunset": ["20:00"],
        },
    }
    result = formatter.format_weather(data, place_label="Москва")
    assert "Москва" in result
    assert "<b>20°C</b>" in result
    assert "<b>18°C</b>" in result
    assert "<b>5 м/с</b>" in result

    assert "📍 Москва\n\nПогода сейчас:" in result


def test_format_weather_no_place():
    data = {
        "current": {
            "temperature_2m": 10,
            "apparent_temperature": 8,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [12],
            "temperature_2m_min": [7],
            "precipitation_probability_max": [20],
            "sunrise": ["07:00"],
            "sunset": ["19:00"],
        },
    }
    result = formatter.format_weather(data)
    assert "Погода сейчас" in result
    assert "<b>10°C</b>" in result
    assert "(ощущается как <b>8°C</b>)" in result
    assert "<b>2 м/с</b>" in result
    assert "Макс: <b>12°C</b>" in result
    assert "Мин: <b>7°C</b>" in result
    assert "Вероятность осадков (макс): <b>20%</b>" in result
    assert "Восход: 07:00" in result
    assert "Закат: 19:00" in result


def test_format_weather_missing_fields():
    data = {
        "current": {
            "temperature_2m": None,
            "apparent_temperature": None,
            "wind_speed_10m": None,
            "weather_code": None,
        },
        "daily": {},
    }
    result = formatter.format_weather(data, place_label="Test")
    assert "Test" in result
    assert "Температура: <b>None°C</b>" in result
    assert "ощущается как" not in result
    assert "Ветер: <b>None м/с</b>" in result
    assert "Макс: <b>None°C</b>" in result
    assert "Мин: <b>None°C</b>" in result
    assert "Вероятность осадков (макс): <b>None%</b>" in result
    assert "Восход: —" in result
    assert "Закат: —" in result


def test_format_weather_partial_daily():
    data = {
        "current": {
            "temperature_2m": 5,
            "apparent_temperature": 3,
            "wind_speed_10m": 1,
            "weather_code": 2,
        },
        "daily": {
            "temperature_2m_max": [8],
            "precipitation_probability_max": [0],
        },
    }
    result = formatter.format_weather(data, place_label="Partial")
    assert "Partial" in result
    assert "<b>5°C</b>" in result
    assert "(ощущается как <b>3°C</b>)" in result
    assert "<b>1 м/с</b>" in result
    assert "Макс: <b>8°C</b>" in result
    assert "Мин: <b>None°C</b>" in result
    assert "Вероятность осадков (макс): <b>0%</b>" in result
    assert "Восход: —" in result
    assert "Закат: —" in result


def test_format_weather_iso_time():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 3,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [18],
            "temperature_2m_min": [12],
            "precipitation_probability_max": [5],
            "sunrise": ["2025-09-07T06:40"],
            "sunset": ["2025-09-07T19:46"],
        },
    }
    result = formatter.format_weather(data, place_label="Nürnberg")
    assert "Nürnberg" in result
    assert "<b>15°C</b>" in result
    assert "<b>14°C</b>" in result
    assert "<b>3 м/с</b>" in result
    assert "Макс: <b>18°C</b>" in result
    assert "Мин: <b>12°C</b>" in result
    assert "Вероятность осадков (макс): <b>5%</b>" in result
    assert "Восход: 06:40" in result
    assert "Закат: 19:46" in result


def test_format_weather_with_tomorrow():

    data = {
        "current": {
            "temperature_2m": 12.1,
            "apparent_temperature": 11.1,
            "wind_speed_10m": 1.63,
            "weather_code": 3,
        },
        "daily": {
            "temperature_2m_max": [22.9, 25.5],
            "temperature_2m_min": [11.7, 14.2],
            "precipitation_probability_max": [0, 15],
            "wind_speed_10m_max": [3.2, 4.1],
            "weather_code": [3, 1],
            "sunrise": ["2025-09-07T06:40", "2025-09-08T06:42"],
            "sunset": ["2025-09-07T19:46", "2025-09-08T19:44"],
        },
    }
    result = formatter.format_weather(data, place_label="Test City")

    assert "Test City" in result
    assert "<b>12.1°C</b>" in result
    assert "<b>1.63 м/с</b>" in result
    assert "Макс: <b>22.9°C</b>" in result
    assert "Мин: <b>11.7°C</b>" in result
    assert "Вероятность осадков (макс): <b>0%</b>" in result

    assert "На завтра (Преимущественно ясно):" in result
    assert "<b>14.2°C</b> ... <b>25.5°C</b>" in result
    assert "☔ <b>15%</b>" in result
    assert "💨 <b>4.1 м/с</b>" in result


def test_format_weather_no_tomorrow_data():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [20],
            "temperature_2m_min": [10],
            "precipitation_probability_max": [5],
            "sunrise": ["07:00"],
            "sunset": ["19:00"],
        },
    }
    result = formatter.format_weather(data)

    assert "На завтра" not in result
    assert "<b>15°C</b>" in result
    assert "Макс: <b>20°C</b>" in result


def test_format_weather_partial_tomorrow_data():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [20, 25],
            "temperature_2m_min": [10, None],
            "precipitation_probability_max": [5, 15],
            "wind_speed_10m_max": [3, None],
            "weather_code": [1, 2],
            "sunrise": ["07:00", "07:01"],
            "sunset": ["19:00", "18:58"],
        },
    }
    result = formatter.format_weather(data)

    assert "На завтра (Переменная облачность):" in result
    assert "<b>—°C</b> ... <b>25°C</b>" in result
    assert "☔ <b>15%</b>" in result

    assert "💨" not in result.split("На завтра")[1]


def test_format_weather_tomorrow_no_weather_code():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [20, 25],
            "temperature_2m_min": [10, 12],
            "precipitation_probability_max": [5, 20],
            "wind_speed_10m_max": [3, 5],
            "weather_code": [1, None],
            "sunrise": ["07:00", "07:01"],
            "sunset": ["19:00", "18:58"],
        },
    }
    result = formatter.format_weather(data)

    assert "На завтра:" in result
    assert "На завтра (" not in result
    assert "<b>12°C</b> ... <b>25°C</b>" in result
    assert "☔ <b>20%</b>" in result
    assert "💨 <b>5 м/с</b>" in result


def test_format_weather_tomorrow_no_wind():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [20, 25],
            "temperature_2m_min": [10, 12],
            "precipitation_probability_max": [5, 20],
            "wind_speed_10m_max": [3, None],
            "weather_code": [1, 2],
            "sunrise": ["07:00", "07:01"],
            "sunset": ["19:00", "18:58"],
        },
    }
    result = formatter.format_weather(data)

    assert "На завтра (Переменная облачность):" in result
    assert "<b>12°C</b> ... <b>25°C</b>" in result
    assert "☔ <b>20%</b>" in result

    tomorrow_section = result.split("На завтра")[1]
    assert "💨" not in tomorrow_section


def test_format_weather_with_day_after_tomorrow():

    data = {
        "current": {
            "temperature_2m": 16.5,
            "apparent_temperature": 16.4,
            "wind_speed_10m": 1.3,
            "weather_code": 3,
        },
        "daily": {
            "temperature_2m_max": [22.6, 25.0, 18.5],
            "temperature_2m_min": [11.6, 12.3, 8.2],
            "precipitation_probability_max": [0, 20, 60],
            "wind_speed_10m_max": [3.2, 4.1, 2.8],
            "weather_code": [3, 1, 61],
            "sunrise": ["06:40", "06:42", "06:44"],
            "sunset": ["19:46", "19:44", "19:42"],
        },
    }
    result = formatter.format_weather(data, place_label="Тест")

    assert "Тест" in result
    assert "<b>16.5°C</b>" in result
    assert "Мин: <b>11.6°C</b>" in result
    assert "Макс: <b>22.6°C</b>" in result
    assert "Вероятность осадков (макс): <b>0%</b>" in result

    assert "На завтра (Преимущественно ясно):" in result
    assert "<b>12.3°C</b> ... <b>25.0°C</b>" in result
    assert "☔ <b>20%</b>" in result
    assert "💨 <b>4.1 м/с</b>" in result

    assert "На послезавтра (Дождь слабый):" in result
    assert "<b>8.2°C</b> ... <b>18.5°C</b>" in result
    assert "☔ <b>60%</b>" in result
    assert "💨 <b>2.8 м/с</b>" in result


def test_format_weather_no_day_after_tomorrow_data():

    data = {
        "current": {
            "temperature_2m": 15,
            "apparent_temperature": 14,
            "wind_speed_10m": 2,
            "weather_code": 1,
        },
        "daily": {
            "temperature_2m_max": [20, 25],
            "temperature_2m_min": [10, 12],
            "precipitation_probability_max": [5, 15],
            "wind_speed_10m_max": [3, 4],
            "weather_code": [1, 2],
            "sunrise": ["07:00", "07:01"],
            "sunset": ["19:00", "18:58"],
        },
    }
    result = formatter.format_weather(data)

    assert "На послезавтра" not in result

    assert "На завтра" in result
    assert "<b>12°C</b> ... <b>25°C</b>" in result
