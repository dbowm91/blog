# Contributing to DevLog

Thank you for your interest in contributing!

## Development Setup

The quickest path is the bundled setup script, which creates a virtual
environment, installs the Python and Node dependencies, generates a `.env` with
a random `SECRET_KEY` and `ADMIN_PASSWORD`, copies `config.toml.example` to
`config.toml`, runs the database migrations, and builds the frontend assets:

```bash
./scripts/setup-dev.sh
```

The bundled setup script creates the virtual environment as `venv/` (not
`.venv/`). To do it by hand:

```bash
# Clone and setup
git clone https://github.com/dbowm91/blog.git
cd blog

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend dependencies
npm ci

# Create the database
export FLASK_APP=run:app
flask db upgrade

# Build frontend assets (required — the app serves hashed assets from the
# Vite manifest)
npm run build

# Run development server
export ADMIN_PASSWORD=test-password-123
export SECRET_KEY=test-secret-key-test-secret-key-1234
python run.py
```

`python-dotenv` loads `.env` automatically, so `SECRET_KEY` and
`ADMIN_PASSWORD` only need to be exported when `.env` is absent.

## Running Tests

```bash
# All tests (requires Playwright for E2E)
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python -m pytest tests/ -v

# Unit tests only (faster)
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python -m pytest tests/ --ignore=tests/e2e -v

# With coverage
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing

# Parallel execution
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python -m pytest tests/ -n auto
```

`ADMIN_PASSWORD` must be set for every run — the tests read it from the
environment so they stay in sync with the configured value.

The E2E suite in `tests/e2e/` uses its own session-scoped app fixture and a
separate database, so `pytest tests/e2e/` can be run on its own. It needs
Playwright browsers (`playwright install`).

## Linting and Type Checking

```bash
# Lint and format check
ruff check .
ruff format --check .

# Type check (app and the standalone CLI)
mypy app/ devlog_cli/

# Dependency manifest consistency
python scripts/check_dependency_manifest_consistency.py
```

## Code Style

- **Python**: Follow PEP 8, use `ruff` for linting
- **Type hints**: Use type annotations for function signatures
- **SQLAlchemy**: Use SQLAlchemy 2.0 patterns (`db.session.execute` with `select()`)
- **Templates**: Jinja2 with HTML escaping (`{{ var|e }}`)
- **CSS**: Use CSS custom properties for theming

## Configuration

Configuration comes from three layers, highest precedence first: environment
variables, then `config.toml`, then the built-in defaults.

The typed schema is the source of truth for every field:
`app/config/model.py` holds one frozen dataclass per section (23 sections
plus the top-level `DevLogConfig`). `app/config_legacy.py` re-exports the
historical flat names so existing imports keep working.

When you add or change a configuration field, update `app/config/model.py`
first, then `config.toml.example`, then the loader. Use the CLI to check your
work:

```bash
devlog config check
devlog config explain app.session_lifetime_hours
devlog config show --effective
```

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
npm ci

# Development with hot reload (proxies to http://localhost:5000)
npm run dev

# Production build
npm run build
```

The Vite dev server runs on port 3000 and proxies API requests to the Flask
app on port 5000.

## Database Migrations

Set `FLASK_APP=run:app` first.

```bash
# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade
```

The standalone CLI also exposes the database commands (`devlog db status`,
`devlog db migrate`, `devlog db check`, `devlog db rebuild-search`).

## Key Files

| File | Purpose |
|------|---------|
| `app/__init__.py` | App factory, extensions |
| `app/models.py` | SQLAlchemy models |
| `app/routes/` | Flask blueprints (`admin/`, `public/`, `api/`) |
| `app/services/` | Business logic |
| `app/config/` | Typed configuration package (schema, loader, validation) |
| `app/themes/` | Halloy theme engine (parser, registry, translation) |
| `app/utils.py` | Utilities, sanitization |
| `devlog_cli/` | Standalone operator CLI |
| `tests/` | Test suite |

## GitHub Templates

Before opening an issue or PR, check existing issues. Use the provided templates:

- **Bug Reports**: Include reproduction steps, expected vs actual behavior, and environment info
- **Feature Requests**: Describe the use case and proposed behavior
