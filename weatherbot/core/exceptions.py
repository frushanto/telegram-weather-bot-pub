from datetime import datetime


class BotError(Exception):

    pass


class ConfigurationError(BotError):

    pass


class StorageError(BotError):

    pass


class WeatherServiceError(BotError):

    pass


class WeatherQuotaExceededError(WeatherServiceError):

    def __init__(self, reset_at: datetime) -> None:
        self.reset_at = reset_at
        super().__init__("Weather API daily quota exceeded")


class GeocodeServiceError(BotError):

    pass


class SpamProtectionError(BotError):

    pass


class ValidationError(BotError):

    pass
