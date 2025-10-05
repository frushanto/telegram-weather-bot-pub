from __future__ import annotations

import json
import re
import tomllib
from datetime import datetime
from pathlib import Path

from weatherbot import __release_date__, __version__
from weatherbot.__version__ import (
    RELEASE_NOTES,
    __supported_languages__,
    __version_info__,
)


def test_release_metadata_consistency() -> None:
    project_root = Path(__file__).resolve().parents[1]

    pyproject_data = tomllib.loads(
        (project_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject_data["project"]["version"] == __version__

    readme = (project_root / "README.md").read_text(encoding="utf-8")
    assert f"version-{__version__}-blue" in readme

    locale_files = [
        project_root / "locales" / "en.json",
        project_root / "locales" / "ru.json",
        project_root / "locales" / "de.json",
    ]
    for locale_file in locale_files:
        locale_data = json.loads(locale_file.read_text(encoding="utf-8"))
        assert locale_data["admin_version_whats_new"].endswith(__version__)

    assert f"New in {__version__}" in RELEASE_NOTES


def test_release_date_format() -> None:
    assert re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", __release_date__)


def test_release_date_validity() -> None:
    """Verifies that release date is valid and not in the future."""
    day, month, year = map(int, __release_date__.split("."))
    release_date = datetime(year, month, day)
    now = datetime.now()

    # Date should not be in the future
    assert release_date <= now, f"Release date {__release_date__} is in the future"

    # Date should not be too old (more than 2 years ago)
    days_old = (now - release_date).days
    assert (
        days_old < 730
    ), f"Release date {__release_date__} is too old ({days_old} days)"


def test_version_info_consistency() -> None:
    """Verifies that __version_info__ matches __version__."""
    version_parts = __version__.split(".")
    expected_tuple = tuple(int(part) for part in version_parts)
    assert (
        __version_info__ == expected_tuple
    ), f"Version info {__version_info__} doesn't match version {__version__}"


def test_supported_languages_consistency() -> None:
    """Verifies that __supported_languages__ matches locale files."""
    project_root = Path(__file__).resolve().parents[1]
    locales_dir = project_root / "locales"

    # Get all JSON files in locales directory
    locale_files = list(locales_dir.glob("*.json"))
    assert len(locale_files) > 0, "No locale files found"

    # Verify that language count matches locale files count
    language_count = len(__supported_languages__.split(", "))
    assert language_count == len(locale_files), (
        f"Supported languages count ({language_count}) doesn't match "
        f"locale files count ({len(locale_files)})"
    )
