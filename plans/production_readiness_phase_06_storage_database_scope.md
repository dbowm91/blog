# Phase 6: Storage and Database Feature Scope

## Objective

Make the public release promise honest and technically coherent for storage and database backends. Local filesystem storage plus SQLite can be the stable default. S3 and PostgreSQL should either be fully wired and tested or clearly marked experimental/deferred.

## Problems to Address

The README and docs describe media storage with S3 or local storage. The storage module includes an S3 backend, but runtime requirements do not include `boto3`/`botocore`, and the admin media listing path calls `storage.path()`, which is only valid for local storage. Therefore, S3 is not backend-complete for the admin media page.

The deployment docs describe PostgreSQL migration and `DATABASE_URL`, but the app reads `SQLALCHEMY_DATABASE_URI`, the requirements do not include a PostgreSQL driver, and FTS5-oriented search initialization appears SQLite-specific. PostgreSQL may be aspirational rather than release-ready.

## Scope

This phase covers backend support boundaries, dependencies, media listing abstractions, database documentation, and tests. It does not require implementing full PostgreSQL search unless PostgreSQL is declared a stable release feature.

## Decision Point A: S3 Support

Choose one path.

### Option A1: Make S3 Stable

Required work:

1. Add optional dependencies.

   Add one of:

   - `requirements-s3.txt` containing `boto3` and compatible dependencies.
   - Python project extras if packaging metadata is expanded.
   - Add `boto3` to runtime requirements if S3 is a core feature.

2. Fail fast when S3 is requested but dependencies or credentials are missing.

   Current behavior falls back to local storage if S3 credentials are missing. For production, silent fallback can lose operator intent. Prefer a startup error when `STORAGE_BACKEND=s3` is explicit but required config is missing. If fallback is retained for developer convenience, log it at error/warning level and document it clearly.

3. Extend storage metadata APIs.

   Add a method such as:

   ```python
   def list_file_info(self, prefix: str = "") -> list[StorageFileInfo]
   ```

   where `StorageFileInfo` includes name/key, size, modified time if available, and URL. Implement for local and S3. Use this in the admin media page instead of `storage.path()` plus `os.stat()`.

4. Ensure delete and cleanup behavior works for variants.

   Confirm `_delete_existing_variants`, media deletion, orphan cleanup, and responsive variant generation work for S3 without local filesystem assumptions.

5. Add S3 docs and tests.

   Add tests using a fake storage backend rather than real AWS. The admin media page should render against a non-local backend. Unit tests should prove S3 dependency/config errors are clear.

### Option A2: Mark S3 Experimental/Deferred

Required work:

1. Update README and DEPLOY.md to state local storage is the stable release backend.
2. Move S3 docs to an experimental section.
3. Keep the code if useful, but document known limitations: missing runtime dependency by default, admin media listing limitations, and unverified production path.
4. Ensure default local storage path is robust and tested.

## Decision Point B: PostgreSQL Support

Choose one path.

### Option B1: Make PostgreSQL Stable

Required work:

1. Add runtime driver support.

   Add a PostgreSQL dependency path, preferably optional:

   - `requirements-postgres.txt` with `psycopg[binary]` or `psycopg2-binary`.
   - Or package extras if pyproject is expanded.

2. Align database env vars.

   Phase 1 should support both `SQLALCHEMY_DATABASE_URI` and `DATABASE_URL`. Document one canonical variable and mention the alias.

3. Make search backend database-aware.

   FTS5 is SQLite-specific. For PostgreSQL, either implement `tsvector`/GIN search or disable FTS initialization and use a documented fallback. Do not run SQLite PRAGMA/FTS SQL blindly against PostgreSQL.

4. Add PostgreSQL CI service.

   Add a CI matrix or separate job that starts PostgreSQL, runs migrations, creates app, runs a focused subset of tests, and exercises search behavior.

5. Verify migrations and schema.

   Ensure Flask-Migrate/Alembic migrations represent the full current model set and work on PostgreSQL.

### Option B2: Mark PostgreSQL Experimental/Deferred

Required work:

1. Update docs to say SQLite is the stable release database.
2. Move PostgreSQL content into an experimental migration appendix.
3. Remove claims that PostgreSQL is currently production-supported unless tests exist.
4. Keep `DATABASE_URL` support if simple and useful, but document that non-SQLite paths are not fully release-certified.

## Recommended Release Choice

For the first public production-ready release, prefer:

- Stable: SQLite with WAL on a single server, local filesystem media, Redis for rate limiting/cache/Celery when using Docker.
- Experimental: S3 storage and PostgreSQL until backend-specific tests and docs are complete.

This keeps the release promise narrow and honest while preserving future extension paths.

## Implementation Steps

1. Make an explicit support matrix.

   Add a table to DEPLOY.md or a new docs page:

   | Feature | Stable | Experimental | Notes |
   |---|---|---|---|
   | SQLite | Yes | No | Default single-server DB |
   | PostgreSQL | No or Yes | Yes or No | Depends on implementation choice |
   | Local media | Yes | No | Default media backend |
   | S3 media | No or Yes | Yes or No | Depends on implementation choice |

2. Update README feature bullets.

   Avoid claiming stable S3/PostgreSQL support unless the phase implements and tests them.

3. Fix admin media listing for non-local backend or mark it local-only.

   If S3 remains advertised, this is mandatory. If S3 is experimental, document limitation and keep admin UI stable for local storage.

4. Add startup validation.

   When unsupported/experimental backend combinations are configured, startup should warn or fail clearly rather than partially working. For stable release, a clear failure is better than silent data loss or fallback.

5. Add tests for support matrix.

   Tests should prove local/SQLite path works. If S3/PostgreSQL are stable, tests should cover them. If experimental, tests should cover warning/error behavior.

## Verification Commands

Stable default path:

```bash
ruff check .
ruff format --check .
mypy app
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "storage or media or search or config"
```

If S3 stable path is implemented:

```bash
STORAGE_BACKEND=s3 ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "storage or media"
```

If PostgreSQL stable path is implemented, add a Postgres service and run:

```bash
SQLALCHEMY_DATABASE_URI=postgresql://blog_user:password@localhost/blog \
ADMIN_PASSWORD=test-password-123 \
SECRET_KEY=test-secret-key-test-secret-key-1234 \
python -m pytest tests/ -v --ignore=tests/e2e -k "database or search or api"
```

## Acceptance Criteria

The README and deployment docs no longer overstate backend support. Stable backend paths are tested. Experimental backend paths are labeled clearly and either fail fast or warn loudly when configured. Admin media listing does not call local-only storage APIs when a stable non-local backend is configured.

## Risks

Marking optional features experimental may feel like a capability reduction, but it improves release trust. Conversely, making S3/PostgreSQL stable can expand scope substantially. Do not accept a stable support claim without CI or equivalent reproducible tests.
