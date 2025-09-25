__version__ = "3.0.0"
__version_info__ = (3, 0, 0)
__release_date__ = "25.09.2025"
__supported_languages__ = "Русский, English, Deutsch"

RELEASE_NOTES = """
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

Previous Releases
==================

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
