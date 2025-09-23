# Configuration Guide

This document lists all environment variables and configuration aspects of the Telegram Weather Bot.

## Core Variables

| Variable         | Required   | Default | Description                                                                             |
| ---------------- | ---------- | ------- | --------------------------------------------------------------------------------------- |
| `BOT_TOKEN`      | Yes (prod) | (empty) | Telegram Bot token from @BotFather. Empty is allowed in test mode (warnings logged).    |
| `ADMIN_IDS`      | No         | (empty) | Comma-separated list of Telegram user IDs with admin privileges. Example: `12345,67890` |
| `ADMIN_LANGUAGE` | No         | `ru`    | Default language for admin-related messages (ru, en, de).                               |
| `TIMEZONE`       | No         | `Europe/Berlin` | Default timezone used for scheduled tasks (affects backup scheduling).         |
| `STORAGE_PATH`   | No         | `data/storage.json` | Path to JSON file storing user data.                                            |

## Spam Protection Variables

| Variable                       | Default | Description                                                   |
| ------------------------------ | ------- | ------------------------------------------------------------- |
| `SPAM_MAX_REQUESTS_PER_MINUTE` | 30      | User request limit per minute before rate limiting triggers.  |
| `SPAM_MAX_REQUESTS_PER_HOUR`   | 200     | User request limit per hour.                                  |
| `SPAM_MAX_REQUESTS_PER_DAY`    | 300     | User request limit per day.                                   |
| `SPAM_BLOCK_DURATION`          | 300     | Initial block duration in seconds (5 minutes).                |
| `SPAM_EXTENDED_BLOCK_DURATION` | 3600    | Extended block duration (1 hour) for repeated violations.     |
| `SPAM_MIN_COOLDOWN`            | 1.0     | Minimum seconds between consecutive user requests.            |
| `SPAM_MAX_MESSAGE_LENGTH`      | 1000    | Maximum allowed message length. Longer messages are rejected. |

## Storage & Backup Variables

| Variable                | Default             | Description                                                                                         |
| ----------------------- | ------------------- | --------------------------------------------------------------------------------------------------- |
| `STORAGE_PATH`          | `data/storage.json` | Path to JSON file storing user data. Change to isolate environments or relocate persistent storage. |
| `BACKUP_ENABLED`        | `true`              | Enable daily backup job for storage file. Set to `false` to disable.                                |
| `BACKUP_RETENTION_DAYS` | 30                  | Number of days to keep backup files before cleanup.                                                 |
| `BACKUP_TIME_HOUR`      | 3                   | Local timezone hour to run daily backup (minute is fixed at :05).                                   |
| `TIMEZONE`              | `Europe/Berlin`    | Timezone used for scheduled tasks and backup scheduling.                                            |

Backups are written to `data/backups/` as `storage-YYYYmmdd-HHMMSS.json` and older files are pruned according to retention.


## File Layout

| File                  | Purpose                                       |
| --------------------- | --------------------------------------------- |
| `.env.dev.example`    | Development defaults example.                 |
| `.env.prod.example`   | Production-oriented example (minimal values). |
| `.env.deploy.example` | Deployment helper (SSH + branch settings).    |

## Configuration Loading
- Environment variables are loaded via `python-dotenv` (`load_dotenv()` in `core/config.py`).
- Missing `BOT_TOKEN` logs a warning and allows test usage.
- Invalid `ADMIN_IDS` format raises `ConfigurationError`.

## Adding New Config
1. Add a field to `SpamConfig` or `BotConfig` dataclasses.
2. Extend `from_env()` method with parsing + default.
3. Update this `CONFIG.md`.
4. Add to `.env.*.example` files if user-facing.
5. (Optional) Add validation tests.

## Internationalization (i18n)
- Default fallback language: `ru`.
- Language files in `locales/*.json` must contain identical key sets.
- When adding a translation key: update `ru.json`, then `en.json`, then `de.json`.

## Deployment Notes
- For production: set `BOT_TOKEN` and `ADMIN_IDS` at minimum.
- Consider running under systemd or Docker for resilience.
- Logs can be redirected using shell: `nohup python app.py > bot.log 2>&1 &`.

## Security Considerations
- Never commit real tokens into repository.
- Use separate tokens for development vs production.
- Rotate tokens after suspected leaks.

## Troubleshooting
| Symptom                     | Possible Cause                    | Resolution                     |
| --------------------------- | --------------------------------- | ------------------------------ |
| Bot starts but does nothing | Empty `BOT_TOKEN`                 | Set real token in `.env`       |
| Admin commands not working  | `ADMIN_IDS` empty                 | Populate admin IDs properly    |
| Users blocked often         | Rate limits too low               | Increase SPAM_* thresholds     |
| Long messages rejected      | Exceeds `SPAM_MAX_MESSAGE_LENGTH` | Raise length or instruct users |

---
If something is missing here, open an issue or PR.

## Environment file examples

Add these lines to your `.env` file (use `.env.dev.example` / `.env.prod.example` as templates):

```env
# Core
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789,987654321
ADMIN_LANGUAGE=ru
TIMEZONE=Europe/Berlin
STORAGE_PATH=data/storage.json

# Backup
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_TIME_HOUR=3

# Spam protection (example values)
SPAM_MAX_REQUESTS_PER_MINUTE=30
SPAM_MAX_REQUESTS_PER_HOUR=200
SPAM_MAX_REQUESTS_PER_DAY=300
SPAM_BLOCK_DURATION=300
SPAM_EXTENDED_BLOCK_DURATION=3600
SPAM_MIN_COOLDOWN=1.0
SPAM_MAX_MESSAGE_LENGTH=1000
```
