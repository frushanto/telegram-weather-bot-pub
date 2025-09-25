# Contributing to Telegram Weather Bot

We welcome contributions to the Telegram Weather Bot project! This document outlines the process for contributing and provides guidelines to ensure a smooth collaboration.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git
- Telegram Bot API token (for testing)

### Setup Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/telegram-weather-bot-pub.git
   cd telegram-weather-bot-pub
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   make install
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.dev.example .env.dev
   # Edit .env.dev with your bot token and settings
   ```

   **Security note:** Do NOT commit your `.env.dev` or any `.env` file with real tokens/keys to the repository. Use the provided example files and keep secrets out of version control.

5. **Run tests:**
   ```bash
   make test
   ```

## 🛠 Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### 2. Make Changes
- Follow the existing code style and architecture
- Add tests for new functionality
- Update documentation if needed

### 3. Quality Checks
Before submitting your changes, run:

```bash
# Format code
make format

# Check code quality
make lint

# Run all tests
make test
```

All checks must pass before submitting a pull request.

### 4. Commit Guidelines
Use conventional commits format:
```
type(scope): description

feat(handlers): add new weather alert command
fix(spam): correct rate limiting calculation
docs(readme): update installation instructions
test(i18n): add tests for new language keys
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `style`: Code style changes
- `chore`: Maintenance tasks

## 🏗 Architecture Guidelines

This project follows Clean Architecture principles with comprehensive value object patterns:

- **Domain Layer**: Value objects (`UserProfile`, `ConversationState`) and interfaces
- **Application Layer**: Use cases and business logic with structured return types
- **Infrastructure Layer**: External service implementations
- **Presentation Layer**: UI, formatting, internationalization  
- **Handlers Layer**: Telegram bot handlers using conversation state management

### Key Principles:
1. **Value Object Architecture**: Use immutable data structures throughout all layers
2. **Type Safety**: Prefer structured objects over raw dicts/tuples/primitives
3. **Dependency Inversion**: High-level modules should not depend on low-level modules
4. **Single Responsibility**: Each class/function should have one reason to change
5. **Testability**: All business logic should be unit testable
6. **Immutability**: State changes return new objects instead of mutations
7. **Internationalization**: All user-facing text should use the i18n system

## 🧪 Testing Guidelines

### Test Coverage
- Maintain high test coverage (currently 90%+)
- Write unit tests for business logic
- Write integration tests for external services
- Add tests for new features and bug fixes

### Test Categories:
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests for service interactions
- **End-to-End Tests**: Complete user workflow tests

### Running Tests:
```bash
# All tests
make test

# Specific test file
pytest tests/test_specific_file.py

# With coverage
pytest --cov=weatherbot tests/
```

### Overriding Configuration in Tests
- Use the helper functions from `weatherbot.core.config` instead of patching module globals.
- Typical pattern:
  ```python
  from weatherbot.core.config import BotConfig, set_config, reset_config_provider

  cfg = BotConfig(token="test", admin_ids=[1])
  set_config(cfg)
  try:
      # test logic here
      ...
  finally:
      reset_config_provider()
  ```
- Prefer this approach in fixtures to guarantee the provider is reset even if a test fails.

### Dependency Overrides in Tests
- When you need to swap infrastructure dependencies, prefer the `overrides=` parameters now available on the helper functions in `weatherbot.infrastructure.container` instead of `monkeypatch`.
- Example: override the weather provider in a test while reusing the shared setup logic:
  ```python
  from weatherbot.infrastructure.container import (
      register_external_clients,
      override_weather_service,
  )

  register_external_clients(
      config,
      overrides=override_weather_service(lambda: FakeWeatherService()),
  )
  ```
- This keeps tests declarative and avoids leaking patched globals across test cases.

## 💎 Value Object Development Guidelines

When working with the codebase, follow these patterns:

### Creating New Value Objects
```python
@dataclass
class NewValueObject:
    field1: str
    field2: int
    optional_field: Optional[str] = None
    
    def to_storage(self) -> Dict[str, Any]:
        # Serialization logic
        pass
    
    @classmethod  
    def from_storage(cls, data: Dict[str, Any]) -> "NewValueObject":
        # Deserialization logic
        pass
```

### Handler Patterns
- **DO**: Use conversation manager for state tracking
  ```python
  conversation_manager.set_awaiting_mode(chat_id, ConversationMode.AWAITING_CITY)
  ```
- **DON'T**: Manipulate global state dictionaries directly
  ```python
  # Avoid this pattern:
  awaiting_city_weather[chat_id] = True
  ```

### Service Return Types
- **DO**: Return structured value objects
  ```python
  async def get_admin_stats(self) -> AdminStatsResult:
      return AdminStatsResult(user_count=10, blocked_count=1, top_users=[...])
  ```
- **DON'T**: Return raw dictionaries or tuples
  ```python
  # Avoid this pattern:
  return {"user_count": 10, "blocked_count": 1}
  ```

## 🌍 Internationalization (i18n)

When adding user-facing text:

1. **Add keys to all language files:**
   - `locales/ru.json` (Russian)
   - `locales/en.json` (English) 
   - `locales/de.json` (German)

2. **Use descriptive key names:**
   ```json
   {
     "weather_command_no_city": "Please specify a city name",
     "error_api_unavailable": "Weather service is temporarily unavailable"
   }
   ```

3. **Never hardcode user-facing text in Python code**
4. **Adjust fallback language if needed** (default language = ru)

## 📝 Documentation

### Code Documentation
- Add docstrings to all public methods
- Use type hints for all function parameters and return values
- Comment complex business logic

### README Updates
- Update README.md for new features
- Add examples for new commands
- Update environment variable documentation

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear bug description**
2. **Steps to reproduce**
3. **Expected vs actual behavior**
4. **Environment information** (Python version, OS)
5. **Relevant logs** (without sensitive data)

## 💡 Feature Requests

For new features:

1. **Open an issue first** to discuss the feature
2. **Explain the use case** and benefit
3. **Consider backward compatibility**
4. **Propose implementation approach**

## 🔒 Security

- Never commit sensitive data (tokens, passwords)
- Use environment variables for configuration
- Follow the security guidelines in SECURITY.md
- Report security vulnerabilities privately

## 📋 Code Review Process

1. **All changes require review** from maintainers
2. **Address review feedback** promptly
3. **Keep pull requests focused** on single features/fixes
4. **Update tests and documentation** as needed

## 🎯 Pull Request Checklist

### Release Notes and Documentation

- If your change will be included in a release, add a short "What's new" entry to `weatherbot/__version__.py` under `RELEASE_NOTES` and update `README.md` with a short summary (or reference `weatherbot.__version__.RELEASE_NOTES`).
- Ensure `locales/*` contain any new admin-facing strings (e.g. `admin_version_whats_new`) and add translations for new user-facing messages.
- Keep release notes concise and focused on user-facing changes, bug fixes, and breaking changes.

Before submitting a PR, ensure:

- [ ] Code follows the project style guidelines
- [ ] All tests pass (`make test`)
- [ ] Code is properly formatted (`make format`)
- [ ] No linting errors (`make lint`)
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format
- [ ] No sensitive data in commits

## 📞 Getting Help

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and ARCHITECTURE.md first

## 🙏 Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- GitHub contributors list
- Special mentions for major features

Thank you for contributing to Telegram Weather Bot! 🤖🌤️
