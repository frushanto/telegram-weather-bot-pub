from weatherbot.domain.weather import WeatherReport


def test_weather_report_from_open_meteo_basic():
    payload = {
        "current": {
            "temperature_2m": "12.5",
            "apparent_temperature": 11.0,
            "wind_speed_10m": "3.2",
            "weather_code": "3",
        },
        "daily": {
            "temperature_2m_min": [5.0, 6.0],
            "temperature_2m_max": [15.0, 16.0],
            "precipitation_probability_max": [10, 20],
            "sunrise": ["2025-01-01T07:00", "2025-01-02T07:01"],
            "sunset": ["2025-01-01T16:00", "2025-01-02T16:02"],
            "wind_speed_10m_max": [4.0, 5.0],
            "weather_code": [1, 2],
        },
        "elevation": 150,
    }

    report = WeatherReport.from_open_meteo(payload)

    assert report.current.temperature == 12.5
    assert report.current.wind_speed == 3.2
    assert report.current.weather_code == 3
    assert len(report.daily) == 2
    today = report.daily[0]
    assert today.min_temperature == 5.0
    assert today.max_temperature == 15.0
    assert today.precipitation_probability == 10
    assert today.sunrise == "2025-01-01T07:00"
    assert report.metadata["elevation"] == 150


def test_weather_report_handles_missing_daily_data():
    payload = {
        "current": {
            "temperature_2m": None,
            "apparent_temperature": None,
            "wind_speed_10m": None,
            "weather_code": None,
        },
        "daily": {},
    }

    report = WeatherReport.from_open_meteo(payload)

    assert report.daily == []
    assert report.current.temperature is None
