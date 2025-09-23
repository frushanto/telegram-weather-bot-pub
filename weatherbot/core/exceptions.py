class BotError(Exception):

    pass


class ConfigurationError(BotError):

    pass


class StorageError(BotError):

    pass


class WeatherServiceError(BotError):

    pass


class GeocodeServiceError(BotError):

    pass


class SpamProtectionError(BotError):

    pass


class ValidationError(BotError):

    pass
