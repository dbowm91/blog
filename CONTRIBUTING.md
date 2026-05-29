# Contributing to DevLog

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone and setup
git clone https://github.com/dbowm91/blog.git
cd blog

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run development server
export ADMIN_PASSWORD=test
export SECRET_KEY=test-secret-key-that-is-at-least-32-chars-long
python run.py
```

## Running Tests

```bash
# All tests (requires Playwright for E2E)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python -m pytest tests/ -v

# Unit tests only (faster)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python -m pytest tests/ --ignore=tests/e2e -v

# With coverage
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing

# Parallel execution
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python -m pytest tests/ -n auto
```

## Code Style

- **Python**: Follow PEP 8, use `ruff` for linting
- **Type hints**: Use type annotations for function signatures
- **SQLAlchemy**: Use SQLAlchemy 2.0 patterns (`db.session.execute` with `select()`)
- **Templates**: Jinja2 with HTML escaping (`{{ var|e }}`)
- **CSS**: Use CSS custom properties for theming

## Pull Request Guidelines

1. **Branch naming**: Use descriptive names (e.g., `fix/login-rate-limit`, `docs/docker-quickstart`, `feature/rss-cache`)
2. **Commits**: Clear, descriptive messages explaining the "why"
3. **Tests**: Include tests for new functionality; don't decrease coverage

## Security Requirements

- Never log user PII or credentials
- Use `user.id` instead of username in logs
- Never commit secrets to repository
- Follow the security patterns in `AGENTS.md`

## Frontend Development

```bash
# Install dependencies
unset HTTP_PROXY HTTPS_PROXY
npm install

# Development with hot reload
npm run dev

# Production build
npm run build
```

## Database Migrations

```bash
# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade
```

## Key Files

| File | Purpose |
|------|---------|
| `app/__init__.py` | App factory, extensions |
| `app/models.py` | SQLAlchemy models |
| `app/routes/` | Flask blueprints |
| `app/services/` | Business logic |
| `app/utils.py` | Utilities, sanitization |
| `tests/` | Test suite |

## GitHub Templates

Before opening an issue or PR, check existing issues. Use the provided templates:

- **Bug Reports**: Include reproduction steps, expected vs actual behavior, and environment info
- **Feature Requests**: Describe the use case and proposed behavior
- **Pull Requests**: Reference related issues, describe changes, and confirm tests pass