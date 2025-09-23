import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class Localization:
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "ru"
        self.load_translations()

    def load_translations(self):

        repo_locales = Path(__file__).parent.parent.parent / "locales"
        package_locales = Path(__file__).parent.parent / "locales"

        if repo_locales.exists():
            locales_path = repo_locales
        else:
            locales_path = package_locales
        for locale_file in locales_path.glob("*.json"):
            lang_code = locale_file.stem
            try:
                with locale_file.open("r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
                logger.info(f"Loaded translations for {lang_code} from {locale_file}")
            except Exception as e:
                logger.error(
                    f"Failed to load translations for {lang_code} at {locale_file}: {e}"
                )

    def get(self, key: str, lang: str = None, **kwargs) -> str:

        if lang is None:
            lang = self.default_language

        if lang in self.translations and key in self.translations[lang]:
            text = self.translations[lang][key]

        elif (
            self.default_language in self.translations
            and key in self.translations[self.default_language]
        ):
            text = self.translations[self.default_language][key]

        if not (
            (lang in self.translations and key in self.translations[lang])
            or (
                self.default_language in self.translations
                and key in self.translations[self.default_language]
            )
        ):
            if "default" in kwargs:
                return kwargs.pop("default")
            logger.warning(f"Translation key '{key}' not found for language '{lang}'")
            return key

        try:

            return text.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format parameter {e} for key '{key}'")
            return text

    def get_available_languages(self) -> list:

        return list(self.translations.keys())


i18n = Localization()
