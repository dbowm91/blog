# Comprehensive Improvement Roadmap

This document serves as the unified strategy for the blog project, consolidating all previous improvement plans into a single actionable roadmap. It targets 80%+ test coverage, enhanced security posture, and optimized system performance.

## Status
- **Current State**: 71% Coverage | 7.3/10 Quality Score
- **Targets**: 80%+ Coverage | 8.5/10 Quality Score | 9.5/10 Security Score
- **Current Focus**: Wave 4 (Code Quality Remediation & Cleanup)

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

---

## Wave 4: Immediate Remediation & Cleanup (Current Focus)

**Goal**: Resolve immediate technical debt, finish exception handling (CQ-3), and clean up the filesystem/documentation.

### 4.1 High Priority: CQ-3 Completion (Exception Handling)
Replace remaining broad `except Exception` clauses with specific exception types.
- **[ ]** `app/services/backup.py:99`: Change to `except (OSError, ValueError, SQLAlchemyError)` (Add `from sqlalchemy.exc import SQLAlchemyError`).
- **[ ]** `app/services/backup.py:122`: Change to `except (OSError, ValueError, SQLAlchemyError)`.
- **[ ]** `app/webhook_encryption.py:68`: Change to `except (ValueError, WebhookEncryptionError)`.
- **[ ]** `app/webhook_encryption.py:101`: Change to `except (ValueError, base64.binascii.Error, WebhookEncryptionError)` (Add `import base64.binascii`).
- **[ ]** `app/tasks.py:232`: Change to `except WebhookEncryptionError`.
- **[ ]** `app/utils.py:155`: **KEEP** `except Exception` with comment: `# Intentional: generic error handler decorator per PEP 8`.
- **[ ]** `app/utils.py:310`: Change to `except (ImportError, AttributeError, ValueError)`.
- **[ ]** `app/utils.py:336`: Change to `except (AttributeError, ValueError, TypeError)`.
- **[ ]** `app/routes/admin/media.py:226`: Change to `except (OSError, AttributeError)`.
- **[ ]** `app/__init__.py:426`: Change to `except SQLAlchemyError` (Add `from sqlalchemy.exc import SQLAlchemyError`).
- **[ ]** `app/routes/public/comments.py:45`: Change to `except SQLAlchemyError`.
- **[ ]** `app/routes/admin/backup.py:149`: Change to `except (OSError, ValueError, SQLAlchemyError)`.
- **[ ]** `app/backup_integrity.py:79`: Change to `except (OSError, ValueError, TypeError)`.

### 4.2 Medium Priority: Structural & Documentation Cleanup
- **[ ]** **Update AGENTS.md Index**: Add `app/routes/public/AGENTS.override.md`; update "Routes" purpose to `"General routing concerns, API authentication, RSS feeds, error handlers"`.
- **[ ]** **Document Admin Sub-Packages**: Update `app/routes/admin/AGENTS.override.md` for `helpers/` and `posts/` sub-packages.
- **[ ]** **Clean Filesystem**: `rm -rf .venv/` (standard is `venv/`), `rm -rf app/static/node_modules/`, and remove all `.DS_Store` artifacts.
- **[ ]** **Unused Imports Cleanup**:
    - `app/utils.py:11`: Remove duplicate `from typing import Any`.
    - `app/tasks.py:7,10`: Remove `cast` and `Task`.
    - `app/webhook_encryption.py:6`: Remove `Optional`.
    - `app/routes/rss.py:1,13`: Remove `make_response` and `import json`.
    - `app/routes/errors.py:4`: Remove `Any`.
    - `app/routes/admin/auth.py:11,97`: Remove `Response` and `ResponseReturnValue`.
- **[ ]** **Root Entry Point**: Add clarifying docstring to root `backup.py`.

### 4.3 Low Priority: Test Infrastructure
- **[ ]** **Conftest Compliance**: Remove `mock_image_processing` fixture; add autouse fixture `ensure_buffer_disabled` to ensure page view buffer is off during tests.
- **[ ]** **Pytest Config**: Add `addopts = --cov=app --cov-report=term-missing` to `pytest.ini`.

---

## Wave 5: Security Hardening & Performance Optimization

**Goal**: Address high-risk vulnerabilities and performance bottlenecks impacting production stability.

### 5.1 Security Hardening
- **[ ]** **Encrypt TOTP Secrets**: Change `totp_secret` to `String(128)` and use AES-256-GCM.
- **[ ]** **2FA Backup Codes**: Implement 10 hex-based recovery codes for 2FA users.
- **[ ]** **Fix PII in `__repr__`**: Remove email from `Subscriber.__repr__` to prevent log leakage.
- **[ ]** **Admin Rate Limiting**: Add `@limiter.limit("30 per minute")` to 35+ admin POST routes.
- **[ ]** **CSRF Consistency**: Ensure `validate_csrf_token()` is used in all admin POST functions.
- **[ ]** **Secure Dockerfile**: Remove `gcc` after `pip install` to reduce image attack surface.
- **[ ]** **Fix Backup Key Min**: Increase minimum encryption key length from 8 to 12+ chars.

### 5.2 Performance & Stability
- **[ ]** **Fix N+1 in Public Posts**: Use `joinedload` for `series_entries` and `series` in `post()` route.
- **[ ]** **Disable Search Debug Logs**: Move search diagnostic logging from `INFO` to `DEBUG`.
- **[ ]** **Optimize FTS Startup**: Idempotent `init_fts` without unconditional `DROP TABLE`.
- **[ ]** **Missing Model Indexes**: Add `ix_posts_scheduled_publish_at` and `ix_share_events_platform`.
- **[ ]** **Restore Buffer Tests**: Re-enable and fix `test_page_view_buffer.py.bak`.
- **[ ]** **Nginx Fixes**: Fix `X-Forwarded-For` typo and add rate limiting/SSL config.

---

## Wave 6: Architecture & Code Quality

**Goal**: Clean up technical debt and unify service patterns.

### 6.1 Refactoring & Patterns
- **[ ]** **Lazy Loading Optimization**: Change collection relationships to `lazy="selectin"` (Post tags, views, etc.).
- **[ ]** **Tag Service Unification**: Consolidate logic into `app/services/tag.py` and add validation.
- **[ ]** **Slug Helper Consolidation**: Remove redundant model methods; use `app/services/slug.py` directly.
- **[ ]** **Extract Business Logic**: Move logic from models to service layer; break up `create_app()`.
- **[ ]** **Comment Relationships**: Migrate `Comment` model to use `back_populates` instead of `backref`.
- **[ ]** **PII Serialization**: Add `include_email=False` default to `serialize_subscriber`.

---

## Wave 7: Testing & Coverage Push

**Goal**: Reach the 80% coverage target across all modules.

### 7.1 Coverage Gaps
- **[ ]** **Zero-Coverage Modules**: Reach 80%+ for `backup_integrity.py`, `webhooks.py`, and `transaction.py`.
- **[ ]** **Low-Coverage Modules**: Reach 80%+ for `app/routes/admin/posts/revisions.py`, `filters.py`, `storage.py`, `admin/users.py`, `page_view_buffer.py`, and `scheduler.py`.
- **[ ]** **Security Coverage**: Add account lockout, CSRF bypass, and rate limiting tests.
- **[ ]** **E2E Testing**: Add full flows for post creation, image uploads, and comments.

### 7.2 Test Infrastructure Improvements
- **[ ]** **Benchmark Thresholds**: Tighten FTS5 search thresholds (e.g., 0.1s → 0.01s).
- **[ ]** **Parallel Execution**: Add `pytest-xdist` to dev dependencies for faster CI runs.
- **[ ]** **Property-Based Tests**: Expand Hypothesis coverage for filters and slug generation.

---

## Wave 8: Infrastructure, Monitoring & CI/CD

**Goal**: Enhance observability and deployment efficiency.

### 8.1 Monitoring & Health
- **[ ]** **Health Check Metrics**: Add Redis, Celery, and backup freshness to `/health`.
- **[ ]** **Centralized Logging**: Integrate ELK/Loki for log shipping.
- **[ ]** **Prometheus Export**: Implement `prometheus_client` for request timing metrics.
- **[ ]** **Docker Polish**: Resource limits in Compose; multi-stage build in Dockerfile.

### 8.2 CI/CD Improvements
- **[ ]** **Security Scanning**: Add `trivy` or `pip-audit` to Github Actions.
- **[ ]** **Multi-Python Testing**: Test across Python 3.12 and 3.13.
- **[ ]** **E2E in CI**: Enable browser-based tests in the CI pipeline using Docker.

---

## Wave 9: Feature Completion, Frontend & Documentation

**Goal**: Finalize public-facing features and improve user experience.

### 9.1 Public APIs & Feeds
- **[ ]** **RSS/JSON Feeds**: Implement RSS 2.0 and JSON Feed 1.1 with caching.
- **[ ]** **API Versioning**: Prefix endpoints with `/api/v1/`.
- **[ ]** **Search Fallback**: Implement SQL `LIKE` fallback for environments without FTS5.
- **[ ]** **SMTP Efficiency**: Offload large newsletter sends (>100) to Celery.

### 9.2 Frontend Polish
- **[ ]** **Brotli Compression**: Enable Brotli in Nginx and pre-compress assets.
- **[ ]** **Asset Optimization**: Bundle Prism.js through Vite; critical CSS extraction.
- **[ ]** **Snippet Scaling**: Batch `post_id` lists in `get_search_snippets` (SQLite limit).

### 9.3 Documentation & Scaling
- **[ ]** **`CONTRIBUTING.md`**: Setup guides, test instructions, and code style.
- **[ ]** **`SECURITY.md`**: Vulnerability reporting policy.
- **[ ]** **`ARCHITECTURE.md`**: System design and data flow.
- **[ ]** **MkDocs Setup**: Material theme for documentation.
- **[ ]** **AVIF Support**: Better image compression (requires Pillow 11.2.0+).
- **[ ]** **Vite Code Splitting**: Reduce initial bundle size.
- **[ ]** **Backup Isolation**: Move backup task to separate process to avoid web blocking.
- **[ ]** **PostgreSQL FTS**: Abstraction for PostgreSQL search compatibility.
