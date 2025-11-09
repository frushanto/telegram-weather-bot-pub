__version__ = "3.1.3"
__version_info__ = (3, 1, 3)
__release_date__ = "09.11.2025"
__supported_languages__ = "Русский, English, Deutsch"

RELEASE_NOTES = """
🎉 New in 3.1.3
---------------
- 🔒 Security: Redacts Telegram bot token from logs (masking tokens in URLs like https://api.telegram.org/bot<token>/… as ***REDACTED***)
- 🔇 Noise reduction: Lowered httpx/urllib3 log level to WARNING to avoid accidental token exposure
- 🧪 Tests: Added logging redaction tests; CI green
- 🌍 i18n: Updated admin “What’s new” strings to 3.1.3 in ru/en/de

Previous Releases
==================

🎉 New in 3.1.2
---------------
- 🛠️ Robust keyboard button matching: prevents Help button misinterpretation across ru/en/de when Telegram sends text without emoji or with unicode variations
- � Telegram keyboard caching fix: buttons now work correctly when users change languages (client-side keyboard cache no longer causes button misrouting)
- �🔁 Scheduled delivery retry policy: configurable retry attempts and delays for subscription weather; graceful fallback message when provider is unavailable
- 🧪 Tests and quality: added normalization tests and keyboard caching tests (287 total); CI green across format, lint, tests, and security
- 🌍 i18n parity: localization keys updated consistently in all languages

🎉 New in 3.1.1
---------------
- ✨ Multilingual command menus: Automatic per-chat command localization using Telegram's setMyCommands API
- ✨ Event-driven language updates: Commands automatically refresh when users change language via UserLanguageChanged event
- ✅ Clean Architecture: Command menu management isolated in presentation layer with event-driven updates
- 🌍 Full i18n support: Command descriptions in English, Russian, and German
- 📝 LRU caching: Efficient command menu caching to reduce API calls
- 🧪 Full test coverage: 14 new tests for command menu functionality (total 256 tests passing)

🎉 New in 3.1.0
---------------
- ✅ Release metadata aligned across packaging, documentation, and localization
- ✅ Documentation refreshed with concise 3.1.0 highlights for operators and admins
- ✅ Dependency container bootstrap clarified with maintainer-facing guidance
- ✅ Repository hygiene improvements by dropping outdated coverage artefacts

🎉 New in 3.0.0
---------------
- ✅ Value Object Architecture: Complete migration to immutable value objects throughout all layers
- ✅ Conversation State Management: New ConversationStateManager with structured state tracking
- ✅ Admin System Overhaul: New AdminApplicationService with structured value object returns
- ✅ Admin Value Objects: AdminStatsResult, AdminUserInfo, AdminConfigSnapshot, AdminTestWeatherResult
- ✅ Weather Quota System: Global API quota management with notifications (WeatherApiQuotaManager)
- ✅ Enhanced Type Safety: Comprehensive type system with rich domain objects (UserProfile, UserHome, UserSubscription)
- ✅ Improved Testing: 218 tests passing with enhanced value object testing patterns
- ✅ Clean Architecture: Enhanced DDD implementation with pure value object patterns
- ✅ Modular DI Container: Enhanced dependency injection with override capabilities
- ✅ Documentation Updates: Comprehensive architecture and contributing guidelines updates
- ⚠️  BREAKING CHANGES: Handler layer now uses structured conversation state instead of global dicts

✨ New in 2.2.0
---------------
- ✅ Subscriptions: Support for time zones in daily subscriptions (timezone-aware scheduling)
- ✅ Makefile: Correct `.env` loading on POSIX/Windows and improved developer workflow

🐛 New in 2.1.2
---------------
- ✅ Removed non-functional coverage badge workflow to prevent CI failures
- ✅ Cleaned up GitHub Actions workflows
- ✅ Fixed CI workflow issues and documentation

🔧 New in 2.1.1
---------------
- ✅ Bug fixes and small improvements

🎉 New in 2.1.0
---------------
- ✅ Multilingual onboarding for new users with flag-based language selection
- ✅ Enhanced help system with bot version information
- ✅ Improved language selection UX with inline buttons
- ✅ Seamless first-time user experience
- ✅ Professional bot information display

🔧 New in 2.0.0
---------------
- ✅ Multi-language support (Russian, English, German)
- ✅ Configurable admin language via ADMIN_LANGUAGE environment variable
- ✅ Enhanced internationalization system
- ✅ Improved user experience with language switching
- ✅ Better error handling and spam protection
- ✅ Full language support: Russian (ru), English (en), German (de)
- ✅ Admin features: Configurable command language, enhanced localization, improved rights management

🔧 New in previous versions
---------------------------
- ✅ Clean architecture with dependency injection container
- ✅ Better separation of concerns
- ✅ Enhanced testing framework
- ✅ Production-ready configuration
"""
