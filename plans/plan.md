# Comprehensive Improvement Roadmap

This document serves as the unified strategy for the blog project, consolidating all previous improvement plans into a single actionable roadmap. It targets 80%+ test coverage, enhanced security posture, and optimized system performance.

## Status
- **Current State**: ~37% Coverage | 8.0/10 Quality Score
- **Targets**: 80%+ Coverage | 8.5/10 Quality Score | 9.5/10 Security Score
- **Current Focus**: Mostly Complete (remaining items require significant scope/big rewrites)

---

## Historical Reference (Completed Waves)

### Wave 1: Security & Stability (May 2026)
- Fixed S-1 (FTS SQL Injection) and S-2 (CSS Injection).
- Added S-3 (Webhook Encryption).
- Improved test stability and fixed CQ-3 exception handling in core modules.

### Wave 2: Refactoring & Performance (May 2026)
- Fixed N+1 queries in series routes.
- Added missing indexes.
- Modularized API routes and centralized `generate_slug()`.

### Wave 3: Features & Future (May 2026)
- Added CDN support and enhanced S3 security.
- Implemented performance benchmarking.
- Corrected S-1 fix to use individual bindparams for SQLite.
- Added `generate_slug()` to `Page` and `Series` models.

### Wave 4: Immediate Remediation & Cleanup (May 2026) - ✅ COMPLETED
- Fixed all remaining CQ-3 exception handling (13 files updated).
- Updated AGENTS.md and AGENTS.override.md documentation.
- Removed unused imports across codebase.
- Updated pytest.ini with coverage options; replaced mock_image_processing with ensure_buffer_disabled fixture.

### Wave 5: Security Hardening & Performance Optimization (May 2026) - ✅ COMPLETED
- Fixed Subscriber PII leak in __repr__.
- Secured Dockerfile (removed gcc post-install).
- Increased backup encryption key minimum to 12 chars.
- Fixed N+1 in public post view.
- Changed FTS debug logs to DEBUG level.
- Optimized FTS initialization (no unconditional DROP TABLE).
- Added missing database indexes.
- Restored page view buffer tests.

### Wave 6: Architecture & Code Quality (May 2026) - ✅ COMPLETED
- Migrated Comment model from backref to back_populates (fixed parent relationship).
- Added include_email=False default to serialize_subscriber for PII protection.

### Wave 7: Testing & Coverage Push (May 2026) - ✅ COMPLETED
- **Zero-Coverage Modules**: Added tests for `backup_integrity.py` (353 lines), `webhooks.py` (286 lines), `transaction.py` (86 lines).
- **Low-Coverage Modules**: Added tests for `revisions.py`, `filters.py`, `admin/users.py`, `page_view_buffer.py`, `scheduler.py`.
- **Security Coverage**: Added account lockout, CSRF bypass, and rate limiting tests.
- **Property-Based Tests**: Added parametrize-based tests for filters and slug generation.
- **Bug Fixed**: `app/webhooks.py` - Fixed `create_webhook_event` session ID issue.
- **Bug Fixed**: `app/routes/public/posts.py` - Added missing `PostSeries` import.

### Wave 8: Infrastructure, Monitoring & CI/CD (May 2026) - ✅ COMPLETED
- **Health Check Metrics**: Added Redis, Celery, and backup freshness checks to `/health` endpoint.
- **Prometheus Export**: Added `prometheus_client` middleware for request timing metrics at `/metrics`.
- **Docker Polish**: Multi-stage build in Dockerfile (builder stage + final stage).
- **CI/CD Improvements**: Added pip-audit job, multi-Python testing (3.12, 3.13), E2E tests in CI.
- **Bug Fixed**: Health check logic now only considers critical checks for overall status (optional services like Redis don't affect "degraded" status).

### Wave 9: Feature Completion, Frontend & Documentation (May 2026) - ✅ COMPLETED
- **Snippet Scaling**: Modified `get_search_snippets` to batch post_ids in chunks of 500 to handle SQLite parameter limits.
- **Backup Isolation**: Added `run_backup_task` Celery task to run backups asynchronously in a worker.

---

## Deferred Items (Require Significant Scope/Big Rewrites)

These items are deferred due to scope or technical complexity:

- **TOTP encryption**: Requires encryption helpers, model changes, UI
- **2FA backup codes**: Requires UI + model changes
- **Admin rate limiting**: Requires testing 35+ routes
- **PostgreSQL FTS abstraction**: Significant architecture change
- **Vite code splitting**: Frontend scope
- **AVIF support**: Requires Pillow 11.2.0+
- **Brotli compression**: Nginx config change, frontend scope
- **Asset optimization (Prism.js bundling, critical CSS)**: Frontend scope

---

## Testing Notes

### Running Tests
```bash
# All tests (requires Playwright browsers installed in .venv)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ -v

# Without E2E tests (if Playwright not installed):
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e

# Install Playwright in .venv:
.venv/bin/pip install pytest-playwright && .venv/bin/playwright install chromium
# Current test count: ~600+ (unit + E2E)
```

### Test Coverage Key Files
- `app/backup_integrity.py`: 65%+ coverage (new tests)
- `app/webhooks.py`: 95%+ coverage (new tests)
- `app/transaction.py`: 65%+ coverage (new tests)
- `app/routes/admin/posts/revisions.py`: 35%+ coverage (new tests)
- `app/routes/admin/users.py`: 20%+ coverage (new tests)

### Page View Buffer Test Issues
- The buffer can cause test interference when running full suite
- Disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- Use autouse fixture to ensure buffer stays disabled

### Database Session Issues
- `db.session.refresh()` fails if object not in current session
- Fix: Re-query from database instead of using `refresh()`
