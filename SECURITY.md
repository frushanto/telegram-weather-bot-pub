# Security Policy

## Sensitive Data Protection

### Environment Variables
- Never commit `.env` files to the repository
- Use `.env.example` files as templates
- Always use different tokens for development and production

### Files to Keep Private
- `.env.dev` - Development environment configuration
- `.env.prod` - Production environment configuration  
- `.env.deploy` - Deployment configuration
- `data/storage.json` - User data storage

### Safe Defaults
- All example files use placeholder values
- No real tokens, IDs, or IP addresses in public code
- Test data uses RFC-compliant placeholder values

### Reporting Security Issues
If you discover a security vulnerability, please create an issue or contact the maintainer directly.

### Development Guidelines
1. Use environment variables for all sensitive configuration
2. Never hardcode tokens, passwords, or API keys
3. Use `.gitignore` to prevent accidental commits of sensitive files
4. Regularly review commits for accidentally included sensitive data
