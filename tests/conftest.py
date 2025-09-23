import pytest

from weatherbot.infrastructure import state


@pytest.fixture(autouse=True)
def clear_state():

    state.awaiting_sethome.clear()
    state.awaiting_city_weather.clear()
    state.awaiting_subscribe_time.clear()
    state.last_location_by_chat.clear()
    yield

    state.awaiting_sethome.clear()
    state.awaiting_city_weather.clear()
    state.awaiting_subscribe_time.clear()
    state.last_location_by_chat.clear()
