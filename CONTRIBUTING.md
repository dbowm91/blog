# Contributing to DevLog

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone and setup
git clone <repo-url>
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

1. **Branch naming**: Use `waveN-description` format (e.g., `wave5-fix-n-plus-one`)
2. **Commits**: Clear, descriptive messages explaining the "why"
3. **Tests**: Include tests for new functionality; don't decrease coverage
4. **Updates**: Update `plans/plan.md` if changes affect planned items

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
| `plans/plan.md` | Development roadmap |