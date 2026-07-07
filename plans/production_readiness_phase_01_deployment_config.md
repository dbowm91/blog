# Phase 1: Deployment Configuration Correctness

## Objective

Make the default deployment and setup paths deterministic. Empty environment variables must not override valid defaults. Documentation and code must agree on canonical environment variable names. A fresh clone using documented setup should start without hidden shell assumptions.

## Problems to Address

The current Compose file injects several optional variables as empty strings. The application often treats mere presence in `os.environ` as an explicit override. This creates failure modes where a user follows the documented Docker path and receives an empty SQLAlchemy URI, an empty Redis cache URL, or other invalid values.

The deployment guide documents `DATABASE_URL` for PostgreSQL, but the app reads `SQLALCHEMY_DATABASE_URI`. The setup script writes `.env`, but the Python app does not automatically load `.env`, and `python-dotenv` is not a runtime dependency. The README says setup starts the dev server, but the script only prints startup instructions.

## Scope

This phase covers environment parsing, config normalization, setup ergonomics, and config documentation. It does not redesign the config system or add a full settings UI.

## Implementation Steps

1. Add a small environment helper in `app/config.py` for optional strings.

   Suggested helper behavior:

   ```python
   def _env_str(key: str, default: str = "") -> str:
       value = os.environ.get(key)
       if value is None or value == "":
           return default
       return value
   ```

   Keep `_env()` if needed for non-string values, but use the normalized helper for URL/secret/string config where an empty string means unset.

2. Normalize database URI selection in `create_app()`.

   Current behavior checks `if "SQLALCHEMY_DATABASE_URI" in os.environ`. Replace it with a normalized resolver that supports both names:

   - Prefer `SQLALCHEMY_DATABASE_URI` when non-empty.
   - Fall back to `DATABASE_URL` when non-empty, for compatibility with common platform conventions and existing docs.
   - Fall back to `sqlite:///<instance_path>/blog.db`.

   Do not let an empty env var produce an empty SQLAlchemy URI.

3. Normalize Redis/cache URL handling.

   In production cache config, use `os.environ.get("CACHE_REDIS_URL") or os.environ.get("REDIS_URL") or "redis://localhost:6379/0"`.

   In Docker Compose, prefer setting `CACHE_REDIS_URL=${CACHE_REDIS_URL:-redis://redis:6379/0}` rather than injecting an empty string. Do the same for any optional but URL-like value where the service default is known.

4. Normalize Celery broker handling.

   `CELERY_BROKER_URL` appears in Compose, but `app/celery_app.py` reads `REDIS_URL`. Either remove `CELERY_BROKER_URL` from docs/Compose if unsupported, or update Celery config to prefer `CELERY_BROKER_URL` when non-empty and use `REDIS_URL` as fallback.

   Avoid documenting unsupported env vars.

5. Decide how `.env` is loaded in local development.

   Preferred low-friction option: add `python-dotenv` to development/runtime dependencies and load it early, before `app.config` is imported. If adding the dependency is undesirable, update `setup.sh` and docs to explicitly instruct:

   ```bash
   set -a
   source .env
   set +a
   python run.py
   ```

   The key requirement is that `./setup.sh` must leave the user with a documented command that actually supplies `SECRET_KEY` and `ADMIN_PASSWORD` to the process.

6. Fix README Quick Start language.

   Remove the claim that `./setup.sh` starts the dev server unless the script is changed to do so. Prefer explicit wording: setup creates a venv, installs dependencies, writes `.env`, creates directories, and prints the next command.

7. Introduce `config.toml.example` and local config convention.

   The app currently raises an error telling users to copy `config.toml.example`, but the repository contains `config.toml`. Make the convention consistent:

   - Add `config.toml.example` with safe public defaults.
   - Add `config.toml` to `.gitignore`.
   - Keep or remove committed `config.toml` depending on migration preference. For public release, prefer removing committed local config in a separate PR after ensuring setup copies the example.
   - Update setup script to copy `config.toml.example` to `config.toml` when absent.

8. Validate `SESSION_COOKIE_SECURE` and local development docs.

   Production must keep secure cookies enabled. Local HTTP development needs a documented way to set `SESSION_COOKIE_SECURE=false`. Ensure setup/dev docs explain this without weakening production defaults.

## Tests to Add or Update

Add config tests that exercise:

- Empty `SQLALCHEMY_DATABASE_URI` falls back to SQLite.
- Non-empty `SQLALCHEMY_DATABASE_URI` wins over `DATABASE_URL`.
- Empty `CACHE_REDIS_URL` falls back to `REDIS_URL` or the production default.
- `DATABASE_URL` is accepted when `SQLALCHEMY_DATABASE_URI` is absent.
- `CELERY_BROKER_URL`, if supported, is used only when non-empty.

Add a setup smoke test if the test suite has shell-script coverage. At minimum, add a documented manual verification checklist.

## Verification Commands

Run:

```bash
ruff check .
ruff format --check .
mypy app
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e
```

Then manually verify fresh local setup:

```bash
rm -rf venv .env instance logs
./setup.sh --dev
# Follow the printed command exactly.
```

Then verify Docker env handling:

```bash
cp .env.example .env
# Fill SECRET_KEY and ADMIN_PASSWORD only.
docker compose --profile production up -d --build
docker compose ps
docker compose logs blog --tail=100
curl -f http://localhost/health || curl -f http://localhost:5000/health
```

## Acceptance Criteria

A fresh user can follow README setup without hitting missing env vars. Docker Compose no longer injects invalid empty values for database/cache defaults. The app supports the documented database env var names. Config tests cover empty string behavior. README, DEPLOY.md, `.env.example`, and setup script all describe the same startup path.

## Risks

Changing config resolution can affect existing deployments that intentionally set empty strings. Treat empty strings as unset only for optional config values where the current empty behavior is invalid. Preserve explicit false-like values where meaningful, such as `SESSION_COOKIE_SECURE=false`.
