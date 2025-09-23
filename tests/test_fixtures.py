import os
import tempfile
from pathlib import Path

import pytest

from weatherbot.core.config import BotConfig, SpamConfig
from weatherbot.core.container import Container
from weatherbot.infrastructure.json_repository import JsonUserRepository


@pytest.fixture
def test_config():

    return BotConfig(token="test_token", admin_ids=[123456], spam_config=SpamConfig())


@pytest.fixture
def temp_storage():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def test_user_repository(temp_storage):

    return JsonUserRepository(temp_storage)


@pytest.fixture
def clean_container():

    container = Container()
    container.clear()
    yield container
    container.clear()
