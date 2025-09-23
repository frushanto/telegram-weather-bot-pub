import pytest

from weatherbot.utils.wmo import WMO_MAPS, wmo_to_text


class TestWMOMultilang:

    def test_wmo_maps_structure(self):

        assert "ru" in WMO_MAPS
        assert "en" in WMO_MAPS
        assert "de" in WMO_MAPS

        ru_codes = set(WMO_MAPS["ru"].keys())
        en_codes = set(WMO_MAPS["en"].keys())
        de_codes = set(WMO_MAPS["de"].keys())
        assert ru_codes == en_codes == de_codes

    def test_wmo_to_text_languages(self):

        assert wmo_to_text(0, "ru") == "Ясно"
        assert wmo_to_text(0, "en") == "Clear sky"
        assert wmo_to_text(0, "de") == "Klarer Himmel"

        assert wmo_to_text(51, "ru") == "Морось слабая"
        assert wmo_to_text(51, "en") == "Light drizzle"
        assert wmo_to_text(51, "de") == "Leichter Nieselregen"

        assert wmo_to_text(95, "ru") == "Гроза"
        assert wmo_to_text(95, "en") == "Thunderstorm"
        assert wmo_to_text(95, "de") == "Gewitter"

    def test_wmo_to_text_fallback(self):

        assert wmo_to_text(999, "ru") == "Код погоды 999"
        assert wmo_to_text(999, "en") == "Weather code 999"
        assert wmo_to_text(999, "de") == "Wettercode 999"

    def test_wmo_to_text_none(self):

        assert wmo_to_text(None, "ru") == "—"
        assert wmo_to_text(None, "en") == "—"
        assert wmo_to_text(None, "de") == "—"

    def test_wmo_to_text_unknown_language(self):

        assert wmo_to_text(0, "fr") == "Ясно"
        assert wmo_to_text(999, "fr") == "Код погоды 999"

    def test_wmo_to_text_default_lang(self):

        assert wmo_to_text(0) == "Ясно"
        assert wmo_to_text(51) == "Морось слабая"

    def test_all_common_codes_coverage(self):

        common_codes = [
            0,
            1,
            2,
            3,
            45,
            48,
            51,
            53,
            55,
            61,
            63,
            65,
            71,
            73,
            75,
            80,
            81,
            82,
            95,
            96,
            99,
        ]
        for code in common_codes:
            for lang in ["ru", "en", "de"]:
                result = wmo_to_text(code, lang)

                assert not result.startswith(f"Weather code {code}")
                assert not result.startswith(f"Код погоды {code}")
                assert not result.startswith(f"Wettercode {code}")

                assert len(result) > 0
