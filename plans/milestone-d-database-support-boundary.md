# Milestone D Plan: Database Support Boundary and Backend-Sensitive Health Checks

## Objective

Make DevLog's database support boundary explicit for public release and ensure backend-specific health checks do not misrepresent or break non-SQLite deployments.

The recommended v1 release position is that SQLite WAL is the supported production database for single-server deployments. PostgreSQL and other engines should remain experimental or planned unless the project implements and validates backend-specific search, health, migration, backup, and operational behavior.

This milestone should reduce public-release risk by making SQLite the clearly supported path and by making non-SQLite behavior graceful rather than accidentally broken.

## Current behavior and risk

The application defaults to SQLite when no `SQLALCHEMY_DATABASE_URI` or `DATABASE_URL` is set. This is appropriate for single-server self-hosted deployment.

However, docs include PostgreSQL migration guidance, and the app has code paths that assume SQLite in health checks and search readiness checks. Examples include:

- Inspecting `sqlite_master` for the `posts_fts` table.
- Running `PRAGMA integrity_check`.
- Describing PostgreSQL migration steps even though search replacement is still called out as future work.

For a public release, this creates two problems:

1. Users may infer that PostgreSQL is production-supported.
2. Operators who try PostgreSQL may hit confusing health-check behavior unrelated to the true app state.

## Target v1 policy

Adopt this policy unless the implementation team decides to fully support PostgreSQL now:

- SQLite WAL is supported and recommended for v1 single-server production.
- PostgreSQL is experimental/planned and not recommended for public v1 production.
- Non-SQLite database URLs should not crash app startup solely because SQLite-only health checks are unavailable.
- Health responses should distinguish unsupported/not-applicable checks from errors.
- Documentation should not present PostgreSQL as a supported production path until search, health, migrations, backup/restore, and CI coverage are complete.

## Files to inspect and modify

Primary code files:

- `app/__init__.py`
- `app/routes/public/meta.py`
- `app/search.py`
- `app/config.py`
- `app/extensions.py`
- `migrations/env.py`

Primary docs/config files:

- `README.md`
- `DEPLOY.md`
- `.env.example`
- `config.toml.example`

Tests:

- Existing health tests.
- Existing search tests.
- Any test fixtures that create app instances with custom database URIs.

## Implementation steps

### Step 1: Add a small database dialect helper

Create a helper that returns the active SQLAlchemy dialect name in a safe, reusable way.

Possible location:

- `app/db_utils.py`
- or a private helper in `app/routes/public/meta.py` if used only there.

Recommended shape:

```python
def get_database_dialect() -> str:
    try:
        return db.engine.dialect.name
    except Exception:
        return "unknown"


def is_sqlite_database() -> bool:
    return get_database_dialect() == "sqlite"
```

If imported from request handlers, ensure it runs under an app context.

### Step 2: Make detailed health backend-aware

In `app/routes/public/meta.py`, update detailed health checks:

#### Search check

Current SQLite FTS check should only run for SQLite.

For SQLite:

- Check `sqlite_master` or another SQLite-safe mechanism for `posts_fts`.
- Return `ok`, `unavailable`, or `error` as it does now.

For non-SQLite:

- Return `unsupported` or `not_applicable` unless a backend-specific search provider is configured and tested.
- Do not run `SELECT name FROM sqlite_master...`.

#### Database integrity check

For SQLite:

- Keep `PRAGMA integrity_check`.

For non-SQLite:

- Return `unsupported` or `not_applicable`.
- Keep the basic database connectivity check as the only portable DB health check.

#### Overall status handling

Decide how `unsupported` and `not_applicable` affect status.

Recommended:

- `unsupported` should not mark health as degraded if the feature is explicitly outside the supported database path, but the response should be clear.
- If the app is configured with a non-SQLite database in production while PostgreSQL is not supported, consider adding a `database_support` check with status `experimental` or `unsupported` so operators see the mismatch.

Example:

```json
{
  "checks": {
    "database": "ok",
    "database_dialect": "postgresql",
    "search": "unsupported",
    "db_integrity": "unsupported"
  }
}
```

### Step 3: Review app startup database integrity check

`create_app()` currently runs a database integrity check after configuring the app. If that check uses SQLite-only PRAGMA unconditionally, gate it by dialect.

For SQLite:

- Run integrity check and log pass/fail.

For non-SQLite:

- Log that SQLite integrity check is skipped because the dialect is not SQLite.
- Do not treat the skip as an error.

### Step 4: Review search initialization

Inspect `app/search.py` and related code for SQLite FTS5 assumptions.

If the search implementation is SQLite-only, document that clearly and avoid implying PostgreSQL support.

Possible implementation paths:

- Minimal v1: retain SQLite FTS5 only, mark non-SQLite search unsupported.
- Larger future path: introduce search provider abstraction with SQLite FTS5 and PostgreSQL tsvector implementations. This should be a later milestone unless required now.

For this milestone, do not attempt a full PostgreSQL search implementation unless the scope is explicitly expanded.

### Step 5: Update docs to state support boundary

README and DEPLOY.md should state:

"SQLite WAL is the supported v1 production database for single-server deployments. PostgreSQL support is experimental/planned and should not be used for production until backend-specific search, health, backup/restore, and migration coverage are complete."

Move PostgreSQL instructions to an experimental appendix, or shorten them to a planning note.

Remove or soften language suggesting that PostgreSQL is a normal production migration path.

### Step 6: Update `.env.example`

In the database section:

```env
# Database defaults to SQLite in the persistent Docker volume.
# PostgreSQL/non-SQLite URLs are experimental for v1 and not recommended for production.
# SQLALCHEMY_DATABASE_URI=postgresql://user:pass@localhost/blog
# DATABASE_URL=postgresql://user:pass@localhost/blog
```

### Step 7: Add tests

Add tests for backend-sensitive health behavior.

Minimum tests:

1. SQLite detailed health includes `search` and `db_integrity` with SQLite checks.
2. SQLite startup integrity check does not fail in normal app creation.
3. Non-SQLite dialect skips SQLite-only search check.
4. Non-SQLite dialect skips PRAGMA integrity check.
5. Non-SQLite detailed health response reports `unsupported`/`not_applicable` rather than `error` for SQLite-only checks.

Testing non-SQLite without running PostgreSQL:

- Prefer monkeypatching `db.engine.dialect.name` or the helper function.
- Keep actual database operations on SQLite test DB where possible.
- Do not add a PostgreSQL service to CI unless the project decides to support it.

### Step 8: Optional startup warning

If `FLASK_ENV=production` and database dialect is not SQLite while v1 support is SQLite-only, log a clear warning:

"Non-SQLite database dialect 'postgresql' is experimental in DevLog v1. SQLite WAL is the supported production database for single-server deployments."

Do not fail startup unless the project wants to actively prevent unsupported production use.

## Edge cases

- SQLAlchemy dialect detection requires an initialized app and engine.
- Some tests may initialize the app before migrations are applied; do not make health checks require a fully populated schema unless existing behavior already does.
- `PRAGMA integrity_check` may be accepted only by SQLite. Never run it against PostgreSQL.
- `sqlite_master` exists only in SQLite. Never use it as a generic search readiness check.
- Search provider config may eventually allow non-SQLite search. Leave room for that by naming statuses carefully.

## Validation commands

Run:

```bash
python -m pytest tests/ --ignore=tests/e2e -v
python -m pytest tests/ -k "health or search or database" -v
ruff check app tests
ruff format --check app tests
mypy app/
docker compose --profile production config
```

If Docker smoke tests are available:

```bash
docker compose --profile production up -d --build
curl -f http://127.0.0.1:5000/health
curl -f "http://127.0.0.1:5000/health?detailed=true&secret=$HEALTH_CHECK_SECRET" || true
docker compose --profile production down -v
```

## Acceptance criteria

- SQLite remains the clearly supported v1 production database.
- PostgreSQL/non-SQLite docs are marked experimental or planned.
- SQLite health checks continue to work.
- Non-SQLite dialects do not trigger SQLite-only queries in health checks.
- Detailed health responses accurately distinguish unsupported/not-applicable checks from real errors.
- App startup does not run SQLite PRAGMA integrity checks against non-SQLite engines.
- Tests cover SQLite and mocked non-SQLite behavior.

## Suggested commit scope

Keep this milestone focused on support boundary, health behavior, startup integrity behavior, and documentation. Do not implement full PostgreSQL search, migrations, or backup support unless the project intentionally expands this milestone into a PostgreSQL support track.
