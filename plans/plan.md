# Comprehensive Improvement Roadmap

This document serves as the unified strategy for the blog project, consolidating all previous improvement plans into a single actionable roadmap. It targets 80%+ test coverage, enhanced security posture, and optimized system performance.

## Status
- **Current State**: ~75% Coverage | 7.8/10 Quality Score
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

### Wave 5: Security Hardening & Performance Optimization (May 2026) - ✅ COMPLETED (partial)
- Fixed Subscriber PII leak in __repr__.
- Secured Dockerfile (removed gcc post-install).
- Increased backup encryption key minimum to 12 chars.
- Fixed N+1 in public post view.
- Changed FTS debug logs to DEBUG level.
- Optimized FTS initialization (no unconditional DROP TABLE).
- Added missing database indexes.
- Restored page view buffer tests.

### Wave 6: Architecture & Code Quality (May 2026) - ✅ COMPLETED (partial)
- Migrated Comment model from backref to back_populates.
- Added include_email=False default to serialize_subscriber for PII protection.

---

## Wave 7: Testing & Coverage Push (In Progress)

**Goal**: Reach the 80% coverage target across all modules.

### 7.1 Coverage Gaps
- [ ] **Zero-Coverage Modules**: Reach 80%+ for `backup_integrity.py`, `webhooks.py`, and `transaction.py`.
- [ ] **Low-Coverage Modules**: Reach 80%+ for `app/routes/admin/posts/revisions.py`, `filters.py`, `storage.py`, `admin/users.py`, `page_view_buffer.py`, and `scheduler.py`.
- [ ] **Security Coverage**: Add account lockout, CSRF bypass, and rate limiting tests.
- [ ] **E2E Testing**: Add full flows for post creation, image uploads, and comments.

### 7.2 Test Infrastructure Improvements
- [x] **Benchmark Thresholds**: Tighten FTS5 search thresholds (e.g., 0.1s → 0.01s).
- [x] **Parallel Execution**: Add `pytest-xdist` to dev dependencies for faster CI runs.
- [ ] **Property-Based Tests**: Expand Hypothesis coverage for filters and slug generation.

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

## Wave 9: Feature Completion, Frontend & Documentation (In Progress)

**Goal**: Finalize public-facing features and improve user experience.

### 9.1 Public APIs & Feeds - ✅ COMPLETED (already implemented)
- [x] **RSS/JSON Feeds**: RSS 2.0 and JSON Feed 1.1 already implemented with caching in `app/routes/rss.py`.
- [x] **API Versioning**: API already at `/api` - adding `/api/v1/` would be breaking change (deferred unless explicitly required).
- [x] **Search Fallback**: LIKE fallback already implemented in `app/search.py` for non-FTS5 environments.
- [x] **SMTP Efficiency**: Large newsletter sends already offloaded to Celery via `send_newsletter_task` in `app/tasks.py`.

### 9.2 Frontend Polish
- [ ] **Brotli Compression**: Enable Brotli in Nginx and pre-compress assets.
- [ ] **Asset Optimization**: Bundle Prism.js through Vite; critical CSS extraction.
- [ ] **Snippet Scaling**: Batch `post_id` lists in `get_search_snippets` (SQLite limit).

### 9.3 Documentation & Scaling - ✅ COMPLETED
- [x] **`CONTRIBUTING.md`**: Setup guides, test instructions, and code style.
- [x] **`SECURITY.md`**: Vulnerability reporting policy.
- [x] **`ARCHITECTURE.md`**: System design and data flow.
- [x] **MkDocs Setup**: Material theme for documentation.
- [ ] **AVIF Support**: Better image compression (requires Pillow 11.2.0+).
- [ ] **Vite Code Splitting**: Reduce initial bundle size.
- [ ] **Backup Isolation**: Move backup task to separate process to avoid web blocking.
- [ ] **PostgreSQL FTS**: Abstraction for PostgreSQL search compatibility.
