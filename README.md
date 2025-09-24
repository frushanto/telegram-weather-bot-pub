# Telegram Weather Bot

[![CI/CD Pipeline](https://github.com/frushanto/telegram-weather-bot-pub/actions/workflows/ci.yml/badge.svg)](https://github.com/frushanto/telegram-weather-bot-pub/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](weatherbot/__version__.py)
[![Python](https://img.shields.io/badge/python-3.12-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-v2.1-ff69b4.svg)](CODE_OF_CONDUCT.md)

## Overview

Telegram Weather Bot is an asynchronous Telegram bot that provides real-time weather information with subscription services, multilingual support, privacy features, and spam protection. Built with emphasis on clean architecture, testability, and excellent user experience.

## ✨ Key Features

- 🌍 **Multilingual Support**: Available in Russian, English, and German
- 🎯 **Enhanced Onboarding**: New users get intuitive language selection with flag buttons
- 📍 **Location-based Weather**: Get weather by city name or GPS location
- 🏠 **Home Location**: Set and manage your home address for quick weather updates
- 📅 **Daily Subscriptions**: Subscribe to daily weather notifications
- 🌐 **Easy Language Switching**: One-click language change with dedicated button
- ℹ️ **Rich Help System**: Comprehensive help with bot version and author information
- 🛡️ **Spam Protection**: Built-in rate limiting and abuse prevention
- 🔒 **Privacy First**: Secure data handling with user data deletion options
- ⚙️ **Admin Controls**: Configurable admin language and management features
- 🏗️ **Clean Architecture**: Built with DDD principles and dependency injection

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- No API key required for default setup (uses Open-Meteo and Nominatim)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/frushanto/telegram-weather-bot-pub.git
   cd telegram-weather-bot-pub
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.dev.example .env   # for local development
   # or
   cp .env.prod.example .env  # for local testing of production settings
   # Edit .env with your configuration
   ```

4. **Configure the bot (important security note)**

   Create `.env` file with the following variables (use the example files as templates):
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   # No WEATHER_API_KEY required for the default Open-Meteo provider
   ADMIN_IDS=123456789,987654321  # Optional: Admin user IDs
   ADMIN_LANGUAGE=en              # Optional: Admin interface language
   DATA_FILE=data/storage.json    # Optional: Data storage file path
   ```

   - **Security note:** Do NOT commit your `.env` file or any real tokens/keys to the repository. The repository keeps only `.env.*.example` files. If you accidentally commit secrets, rotate them immediately and follow git-history cleanup procedures.
   - Prefer using `.env.dev` and `.env.prod` as environment-specific files and keep them out of version control (examples are provided as `.env.dev.example` and `.env.prod.example`).

5. **Run the bot**
   ```bash
   python app.py
   ```

### Docker Setup

1. **Using Docker Compose** (recommended)
   ```bash
   docker-compose up -d
   ```

2. **Using Docker directly**
   ```bash
   docker build -t weather-bot .
   docker run -d --env-file .env weather-bot
   ```

## 📖 Usage

### Basic Commands

- `/start` - Initialize the bot and get welcome message
- `/weather <city>` - Get current weather for specified city
- `/home` - Get weather for your home location (if set)
- `/sethome <city>` - Set your home location
- `/unsethome` - Remove your home location
- `/subscribe` - Subscribe to daily weather notifications
- `/unsubscribe` - Unsubscribe from daily notifications
- `/language` - Change interface language
- `/help` - Show available commands and usage instructions
- `/privacy` - View privacy information
- `/data` - Request your stored data
- `/delete_me` - Delete all your data from the bot

### Admin Commands (if configured)

These commands are available to configured admin users (set `ADMIN_IDS` in your environment):

- `/admin_stats` - Display overall bot usage statistics and top users
- `/admin_user_info <user_id>` - Show detailed info and spam stats for a specific user
- `/admin_unblock <user_id>` - Remove a user from the blocked list
- `/admin_cleanup` - Cleanup old spam protection data and temporary records
- `/admin_version` - Show current bot version, release date and supported languages
- `/admin_help` - Show a help message with admin command descriptions and examples

Examples:

```text
/admin_user_info 123456789
/admin_unblock 123456789
```

### Location Support

The bot supports both text-based city names and GPS coordinates:

1. **Text Input**: Simply type a city name
2. **Location Sharing**: Use `/sethome` to share your location
3. **Home Location**: Set once, use repeatedly with `/home`

### Language Support

Switch between supported languages anytime:
- 🇷🇺 Russian (ru)
- 🇺🇸 English (en)  
- 🇩🇪 German (de)

Use the 🌐 Language button or `/language` command to change.

## 🏗️ Architecture

The bot follows Clean Architecture principles with clear separation of concerns:

```
weatherbot/
├── core/           # Enterprise Business Rules (entities, value objects)
├── domain/         # Domain Layer (business logic, interfaces)
├── application/    # Application Layer (use cases, services)
├── infrastructure/ # Infrastructure Layer (external services, repositories)
├── presentation/   # Presentation Layer (formatters, keyboards)
├── handlers/       # Interface Adapters (command handlers, callbacks)
├── jobs/           # Background Jobs (scheduler, backup)
├── utils/          # Shared Utilities
├── data/           # Example data and storage (data/storage.json)
└── tests/          # Test suite
```

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
make test

# Run tests with coverage
make coverage

# Run specific test file
python -m pytest tests/test_commands.py -v

# Run with coverage report
python -m pytest --cov=weatherbot --cov-report=html
```

## 🔧 Development

### Setup Development Environment

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Run code formatting**
   ```bash
   make format
   ```

### Available Make Commands

```bash
make install       # Install dependencies
make test          # Run tests
make coverage      # Run tests with coverage
make format        # Format code with black and isort
make clean         # Clean temporary files
make docker-build  # Build Docker image
make docker-run    # Run Docker container
```

### Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Code style and standards
- Pull request process
- Issue reporting
- Development workflow

## 📝 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | - | Telegram Bot Token from BotFather |
| `ADMIN_IDS` | ❌ | - | Comma-separated admin user IDs |
| `ADMIN_LANGUAGE` | ❌ | `en` | Admin interface language (en/ru/de) |
| `DATA_FILE` | ❌ | `data/storage.json` | Data storage file path |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `TIMEZONE` | ❌ | `UTC` | Timezone for scheduled tasks |

### Storage

The bot uses JSON file storage by default. The storage includes:
- User preferences (language, home location)
- Subscription settings
- Usage statistics
- Spam protection data

## 🛡️ Privacy & Security

- **Data Minimization**: Only necessary data is stored
- **User Control**: Users can view and delete their data anytime
- **Spam Protection**: Built-in rate limiting and abuse prevention
- **Secure Configuration**: Sensitive data in environment variables
- **Regular Backups**: Automated daily backups (if admin configured)

## 📊 Monitoring & Logging

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Error Tracking**: Comprehensive error handling and logging
- **Performance Metrics**: Request timing and usage statistics
- **Health Checks**: Built-in health monitoring endpoints

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   - Use production-grade environment variables
   - Set appropriate log levels
   - Configure monitoring

2. **Docker Deployment**
   ```bash
   docker-compose up -d
   ```

3. **Health Monitoring**
   - Monitor logs for errors
   - Set up alerting for critical issues
   - Regular backup verification

### Scaling Considerations

- The bot is designed for single-instance deployment
- For high-load scenarios, consider:
  - Database backend instead of JSON storage
  - Redis for session management
  - Load balancing for multiple instances

## 📚 API Documentation

### Weather Data Source

The bot uses Open-Meteo for weather data and Nominatim (OpenStreetMap) for geocoding:
- Open-Meteo: current conditions, daily summaries, and forecasts (no API key required)
- Nominatim: free geocoding service for converting city names to coordinates

### Rate Limits

- Open-Meteo: 1000 calls/day (free tier)
- Telegram Bot API: 30 messages/second
- Internal rate limiting: 5 requests/minute per user

## 🆘 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check BOT_TOKEN validity
   - Verify network connectivity
   - Check logs for errors

2. **Weather data not loading**
   - Verify external provider availability (Open-Meteo)
   - Check API quota limits or service status for Open-Meteo
   - Ensure city name is correct and geocoding (Nominatim) returns results

3. **Language not changing**
   - Restart conversation with /start
   - Check locale files are present
   - Verify language code format

4. **Notifications not working**
   - Check subscription status
   - Verify timezone configuration
   - Ensure bot has message permissions

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python app.py
```

## 📈 Changelog

See `weatherbot/__version__.RELEASE_NOTES` for detailed version history and updates.

## 🆕 What's New — Version 2.2.0

This release introduces timezone-aware scheduling and improves developer workflow:

- **Timezone Support**: Daily weather subscriptions now support user-specific time zones for accurate delivery scheduling.
- **Improved Makefile**: Fixed `.env` file loading on both POSIX and Windows systems for reliable development environment setup.
- **Enhanced Testing**: Added comprehensive tests for DST edge cases and timezone transitions.
- **Developer Experience**: Better cross-platform compatibility and improved CI reliability.

For full release notes see `weatherbot.__version__.RELEASE_NOTES` or the project's changelog when available.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- 📧 **Email**: frushanto@gmail.com
- 💬 **Discussions**: Use GitHub Discussions for questions
- 🐛 **Bug Reports**: File an issue with detailed information
- 💡 **Feature Requests**: Submit enhancement proposals

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot framework
- [Open-Meteo](https://open-meteo.com/) - Weather data provider (used by default)
- [Nominatim / OpenStreetMap](https://nominatim.org/) - Geocoding service for converting city names to coordinates
- [httpx](https://github.com/encode/httpx) - Async HTTP client
- All contributors who helped improve this project

---

**Made with ❤️ by frushanto**