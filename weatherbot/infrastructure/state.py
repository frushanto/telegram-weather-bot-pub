from ..domain.conversation import ConversationStateManager

# Global conversation state manager (will be replaced by dependency injection later)
conversation_manager = ConversationStateManager()

# Legacy compatibility for existing code during migration
awaiting_sethome: dict[int, bool] = {}
awaiting_city_weather: dict[int, bool] = {}
awaiting_subscribe_time: dict[int, bool] = {}
awaiting_language_input: dict[int, bool] = {}
last_location_by_chat: dict[int, tuple[float, float]] = {}
