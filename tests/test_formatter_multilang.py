import pytest

from weatherbot.presentation import formatter


class TestFormatterMultilang:

    def test_format_weather_with_language_param(self):

        data = {
            "current": {"temperature_2m": 20, "weather_code": 0},
            "daily": {
                "temperature_2m_max": [25, 22],
                "temperature_2m_min": [15, 12],
                "weather_code": [0, 51],
                "sunrise": ["07:30"],
                "sunset": ["18:45"],
            },
        }

        result_ru = formatter.format_weather(data, lang="ru")
        assert "Ясно" in result_ru
        assert "На завтра (Морось слабая)" in result_ru

        result_en = formatter.format_weather(data, lang="en")
        assert "Clear sky" in result_en
        assert "Tomorrow (Light drizzle)" in result_en

        result_de = formatter.format_weather(data, lang="de")
        assert "Klarer Himmel" in result_de
        assert "Morgen (Leichter Nieselregen)" in result_de

    def test_format_weather_default_language(self):

        data = {
            "current": {"temperature_2m": 20, "weather_code": 0},
            "daily": {
                "temperature_2m_max": [25],
                "temperature_2m_min": [15],
                "weather_code": [0],
                "sunrise": ["07:30"],
                "sunset": ["18:45"],
            },
        }

        result = formatter.format_weather(data)
        assert "Ясно" in result

    def test_format_weather_day_after_tomorrow_multilang(self):

        data = {
            "current": {"temperature_2m": 20, "weather_code": 0},
            "daily": {
                "temperature_2m_max": [25, 22, 19],
                "temperature_2m_min": [15, 12, 8],
                "weather_code": [0, 51, 95],
                "sunrise": ["07:30"],
                "sunset": ["18:45"],
            },
        }

        result_ru = formatter.format_weather(data, lang="ru")
        assert "На послезавтра (Гроза)" in result_ru

        result_en = formatter.format_weather(data, lang="en")
        assert "Day after tomorrow (Thunderstorm)" in result_en

        result_de = formatter.format_weather(data, lang="de")
        assert "Übermorgen (Gewitter)" in result_de

    def test_format_weather_without_weather_codes(self):

        data = {
            "current": {"temperature_2m": 20},
            "daily": {
                "temperature_2m_max": [25, 22, 19],
                "temperature_2m_min": [15, 12, 8],
                "sunrise": ["07:30"],
                "sunset": ["18:45"],
            },
        }

        for lang in ["ru", "en", "de"]:
            result = formatter.format_weather(data, lang=lang)
            assert len(result) > 0

            if lang == "ru":
                assert "На завтра:" in result
                assert "На послезавтра:" in result
            elif lang == "en":
                assert "Tomorrow:" in result
                assert "Day after tomorrow:" in result
            elif lang == "de":
                assert "Morgen:" in result
                assert "Übermorgen:" in result
