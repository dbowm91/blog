# Master Improvement Plan

**Date:** 2026-04-29
**Status:** COMPLETED
**Summary:** All waves verified complete - 514 tests pass. Post-verification fixes applied: orphaned JS code removed, responsive images srcset implemented.

---

## WAVE 1: Critical Fixes & Infrastructure [COMPLETED]

### 1.1: Fix JS Module Initialization [COMPLETED]
- Route-based dynamic imports in main.js
- All modules export default initialization functions
- Post-verification: Fixed orphaned JS code in bulk.js, lazy-load.js, image-preview.js

### 1.2: Fix IntegrityError Rollback in pages.py [COMPLETED]
- new_page() and edit_page() properly re-apply fields after rollback

### 1.3: Fix Share Platform and JSON Feed Spec Compliance [COMPLETED]
- ALLOWED_SHARE_PLATFORMS uses "hackernews" (not "hn")
- JSON Feed includes content_html field per spec

### 1.4: Fix UI Logic Bugs (Toast, Modal) [COMPLETED]
- Escape key closes modals/menus
- Toast notifications with auto-dismiss

### 1.5: Security: CSS Sanitization & Clean Test Uploads [COMPLETED]
- sanitize_css() strips dangerous properties (url(), expression(), content, etc.)

### 1.6: Health Monitoring & Docker Readiness [COMPLETED]
- /health endpoint with DB, scheduler, FTS checks
- Graceful shutdown in run.py
- Docker/Granian configuration

---

## WAVE 2: Security Hardening & Performance [COMPLETED]

### 2.1: Implement Application-Level Rate Limiting [COMPLETED]
- flask-limiter integrated with configurable storage
- Rate limits on login (5/min), API endpoints, public routes

### 2.2: Account Lockout Mechanism [COMPLETED]
- User.is_locked(), record_failed_login(), reset_failed_login()
- MAX_FAILED_ATTEMPTS and LOCKOUT_DURATION_MINUTES config

### 2.3: Security Cleanup (Race Conditions, CSRF, IP Binding) [COMPLETED]
- CSRF sliding window with hmac.compare_digest()
- IP binding warning on session mismatch
- make_owner() promotes target first, then demotes others

### 2.4: Frontend Performance (Critical CSS, Prism.js) [COMPLETED]
- Critical CSS: Inline CSS in base.html (lines 23-87) covers above-the-fold
- Full style.css loaded asynchronously via media="print" onload
- Prism.js self-hosted (not CDN)

---

## WAVE 3: Backend Refactoring & Scalability [COMPLETED]

### 3.1: Template Filters & Transaction Helpers [COMPLETED]
- post_image_url with g object request-level caching
- reading_time, markdown_safe, sanitize_css filters
- Theme, footer, canonical_url context processors

### 3.2: Cache Optimization & Caching Standard [COMPLETED]
- Tag counts via flask-cache memoization
- invalidate_tag_cache() called on tag changes

### 3.3: APScheduler Persistence & Maintenance [COMPLETED]
- File locking with fcntl for newsletter job
- Manual SMTP try/finally (not with statement)
- yield_per(500) streaming without .all()

### 3.4: Performance Tuning (ASGI, Responsive Images) [COMPLETED]
- Granian ASGI server (run.py exports asgi_app)
- Responsive images: Post-verification fix added srcset support in templates
  - 400_/800_/1200_ variants generated on upload
  - Templates now use srcset with sizes attribute

---

## WAVE 4: Database & Documentation [COMPLETED]

### 4.1: DB Optimization & PostgreSQL Script [COMPLETED]
- All indexes present (ix_posts_published_created, etc.)
- DEPLOY.md has comprehensive PostgreSQL migration guide
- migrations/env.py has render_as_batch=True

### 4.2: Comprehensive Documentation Rewrite [COMPLETED]
- DEPLOY.md: PostgreSQL, nginx, Caddy, Cloudflare, cron, Docker, backups

### 4.3: Final Tooling & Cleanup [COMPLETED]
- All CLI commands: rebuild-search, cleanup-orphaned-images, create-admin, etc.
- Alembic migrations properly configured

---

## WAVE 5: Advanced Features (Optional/Deferred)

1. **S3 Storage:** Implement storage abstraction layer for optional S3-compatible media storage.
2. **Page View Buffer:** Implement in-memory buffer for batching page view writes (for high-traffic sites).
3. **Backup Encryption:** Add GPG encryption support for database backups.

---

## Testing Strategy
- **Unit Tests:** All 514 tests pass (excluding E2E which require Playwright)
- **Verification:** 2026-04-29 - All items verified in code, fixes applied where needed
