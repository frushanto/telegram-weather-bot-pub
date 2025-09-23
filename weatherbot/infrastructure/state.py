awaiting_sethome: dict[int, bool] = {}
awaiting_city_weather: dict[int, bool] = {}
awaiting_subscribe_time: dict[int, bool] = {}
awaiting_language_input: dict[int, bool] = {}
last_location_by_chat: dict[int, tuple[float, float]] = {}
