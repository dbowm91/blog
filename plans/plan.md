# Master Improvement Plan

**Date:** 2026-04-28
**Status:** READY FOR EXECUTION
**Summary:** Consolidate, optimize, and detail 100+ improvements across security, performance, reliability, and documentation.

---

## WAVE 1: Critical Fixes & Infrastructure [Parallelizable]

These items fix broken functionality or prepare the infrastructure for subsequent waves.

### 1.1: Fix JS Module Initialization [CRITICAL]
**Files:** `app/static/js/main.js`, all 19+ modules in `app/static/js/{shared,public,admin}/`
**Context:** Current `main.js` calls module objects as functions, which throws `TypeError`.
**Action:**
1.  Add `export default initXxx;` to the end of every JS module (e.g., `export default initDarkMode;` in `dark-mode.js`).
2.  Update `app/static/js/main.js`:
    ```javascript
    modules.forEach(m => loadModule(m, module => {
        if (typeof module.default === 'function') {
            module.default();
        }
    }));
    ```
3.  **Modules to update:** `shared/dark-mode.js`, `shared/mobile-menu.js`, `shared/lazy-load.js`, `shared/utils.js`, `shared/modal.js`, `shared/nav-dropdown.js`, `shared/filter-select.js`, `shared/prefetch.js`, `public/search.js`, `public/lightbox.js`, `public/toc.js`, `public/share.js`, `public/code-copy.js`, `public/anchor-links.js`, `public/media-copy.js`, `admin/editor.js`, `admin/bulk.js`, `admin/shortcuts.js`, `image-preview.js`, `upload.js`. (`shared/toast.js` already has it).

### 1.2: Fix IntegrityError Rollback in pages.py
**Files:** `app/routes/admin/pages.py` (lines 77-82, 143-148)
**Context:** Database rollback expires SQLAlchemy objects. `pages.py` fails to re-apply field changes after rollback.
**Action:** Follow the pattern in `posts.py`:
1.  In `new_page()` and `edit_page()`, catch `IntegrityError`.
2.  If it's a slug collision, generate a new slug using `_generate_unique_slug(Page, title)`.
3.  **Crucial:** Explicitly re-assign `page.title`, `page.body`, `page.published`, etc. *after* `db.session.rollback()` before trying to commit again.

### 1.3: Fix Share Platform and JSON Feed Spec Compliance
**Files:** `app/templates/_post_content.html`, `app/routes/rss.py`, `app/routes/public.py`
**Action:**
1.  **CB-4:** In `app/templates/_post_content.html`, change `data-platform="hn"` to `data-platform="hackernews"` to match `ALLOWED_SHARE_PLATFORMS` in `public.py`.
2.  **CB-5:** In `app/routes/rss.py:json_feed()`, add `content_html` field to each item containing `post.body` rendered via `markdown_safe` filter. JSON Feed 1.1 requires `content_html` or `content_text`.
3.  **Preview Token:** In `app/routes/public.py:public_preview()`, use `hmac.compare_digest(token, expected_token)` instead of `!=` for timing attack prevention.

### 1.4: Fix UI Logic Bugs (Toast, Modal)
**Files:** `app/static/js/shared/toast.js`, `app/static/js/shared/modal.js`
**Action:**
1.  **Toast:** In `toast.js`, replace `translateY(-100%)` with cumulative pixel offsets using `GAP = 12`. Loop through `toastStack` and set `transform = translateY(-${cumulativeOffset}px)`.
2.  **Modal:** In `modal.js`, add a check for `event.propertyName === 'opacity'` inside the `transitionend` listener to prevent multiple fires (since it also has a transform transition).

### 1.5: Security: CSS Sanitization & Clean Test Uploads
**Files:** `app/routes/admin/settings.py`, `app/static/uploads/`, `tests/conftest.py`
**Action:**
1.  **CSS:** In `settings.py`, wrap `request.form.get("custom_css")` with `sanitize_css()` before assigning to `settings_obj.custom_css`.
2.  **Cleanup:** Manually delete all 1,580+ files in `app/static/uploads/`.
3.  **Fixture:** Add a session-scoped `autouse` fixture to `tests/conftest.py` that clears `UPLOAD_FOLDER` after tests finish.

---

## WAVE 2: Security Hardening & Performance [Parallelizable]

### 2.1: Implement Application-Level Rate Limiting
**Files:** `requirements.txt`, `app/__init__.py`, `app/routes/admin/auth.py`, `app/routes/api.py`
**Action:**
1.  Add `flask-limiter` to requirements.
2.  Initialize `Limiter` in `app/__init__.py` using `get_remote_address`.
3.  Apply `@limiter.limit("5 per minute")` to `/admin/login`.
4.  Apply appropriate limits to API and public subscribe routes.
5.  Configure 429 error handlers for both HTML and JSON responses.

### 2.2: Account Lockout Mechanism
**Files:** `app/models.py`, `app/routes/admin/auth.py`, `app/config.py`
**Action:**
1.  Add `failed_login_count` (int) and `locked_until` (UTCDateTime) to `User` model.
2.  Implement `User.is_locked()`, `record_failed_login()`, and `reset_failed_login()`.
3.  Update `auth.py:login()`: Check `is_locked()` before password check; call `record_failed_login()` on failure and `reset_failed_login()` on success.
4.  Add `MAX_FAILED_ATTEMPTS` (5) and `LOCKOUT_DURATION_MINUTES` (15) to config.

### 2.3: Security Cleanup (Race Conditions, CSRF, IP Binding)
**Files:** `app/routes/admin/users.py`, `app/csrf.py`, `app/routes/admin/__init__.py`
**Action:**
1.  **make_owner():** In `users.py`, promote the target user to admin *first*, then demote all others. Use `db.session.flush()` after promotion.
2.  **CSRF:** When rotating tokens in `users.py` (promote/demote/make_owner), reset the list `session["csrf_tokens"] = [generate_csrf_token()]` instead of setting the singular `session["csrf_token"]`.
3.  **IP Binding:** In `admin_required` decorator, if `SESSION_IP_BINDING` is set to `enforce` and IP changes, call `logout_user()`, clear session, and redirect to login.

### 2.4: Frontend Performance (Critical CSS, Prism.js)
**Files:** `app/templates/base.html`, `app/static/js/main.js`, `app/static/css/style.css`
**Action:**
1.  **Critical CSS:** Inline ~5KB of critical CSS (navbar, hero, first post card) in `base.html` `<head>`. Load main `style.css` asynchronously using `media="print" onload="this.media='all'"` pattern.
2.  **Prism.js:** In `main.js`, implement `loadPrismIfNeeded()` which checks for `pre[class*="language-"]` and dynamically loads `prism.min.js` and `prism-languages.js`. Remove static Prism script tags from `base.html`.

---

## WAVE 3: Backend Refactoring & Scalability [Parallelizable]

### 3.1: Template Filters & Transaction Helpers
**Files:** `app/__init__.py`, New `app/filters.py`, New `app/transaction.py`
**Action:**
1.  **Filters:** Move all template filters from `app/__init__.py` to `app/filters.py`. Implement `register_filters(app)` for registration.
2.  **Transactions:** Create `@transactional` decorator and `commit_with_slug_retry()` helper in `app/transaction.py` to consolidate the 50+ `db.session.rollback()` patterns.

### 3.2: Cache Optimization & Caching Standard
**Files:** `app/__init__.py`, `app/cache.py`, `app/extensions.py`, `requirements.txt`
**Action:**
1.  **Filter Caching:** Add request-level caching (via `g` object) to `reading_time` and `markdown_safe` filters.
2.  **Standardization:** Add `flask-caching` to requirements. Replace custom caching in `app/cache.py`, `context_processors.py`, and admin helpers with `flask-caching` (SimpleCache or Redis).

### 3.3: APScheduler Persistence & Maintenance
**Files:** `app/scheduler.py`, `app/models.py`
**Action:**
1.  **Persistence:** Replace `MemoryJobStore` with `SQLAlchemyJobStore` using the existing SQLite engine. Remove all `fcntl` locking logic.
2.  **Maintenance:** Add 4 periodic jobs: Daily DB Integrity Check (3AM), Daily WAL Checkpoint (4AM), Weekly FTS Integrity Check (Sun 2AM), Daily DB Optimize (1AM).

### 3.4: Performance Tuning (ASGI, Sessions, Responsive Images)
**Files:** `run.py`, `Dockerfile`, `app/routes/admin/helpers/images.py`, `app/models.py`
**Action:**
1.  **Remove ASGI Wrapper:** Remove `WsgiToAsgi` wrapper from `run.py`. Update `Dockerfile` to use `granian --interface wsgi run:app`.
2.  **Redis Sessions:** Migrate to `flask-session` with Redis backend.
3.  **Responsive Images:** Use `Pillow` to generate 400w, 800w, 1200w variants in `_save_image()`. Implement `responsive_image` Jinja filter and update templates to use `srcset`.

---

## WAVE 4: Database & Documentation [Parallelizable]

### 4.1: DB Optimization & PostgreSQL Script
**Files:** `app/models.py`, `app/search.py`, `DEPLOY.md`
**Action:**
1.  **Indexes:** Add `ix_post_revisions_author_id` to `PostRevision`.
2.  **FTS5:** Optimize `get_indexed_terms()` in `search.py` to use `fts5vocab` table instead of querying the posts table.
3.  **PostgreSQL:** Fix the migration script in `DEPLOY.md` (remove non-existent `created_at` from users, fix `body` vs `content` in pages, fix `referrer` in page_views).

### 4.2: Comprehensive Documentation Rewrite
**Files:** `README.md`, `DEPLOY.md`, `AGENTS.md`, New `USAGE.md`, `docs/openapi.yaml`
**Action:**
1.  **README:** Rewrite as task-oriented (not feature-listing). Add "Quick Start", "Troubleshooting" (15 issues), and "FAQ".
2.  **USAGE.md:** Create detailed user guide covering post writing, newsletter management, and admin tasks.
3.  **openapi.yaml:** Add request/response examples for all endpoints.
4.  **AGENTS.md:** Update with latest "Lessons Learned" (JS Init, IntegrityError rollbacks, etc.).

### 4.3: Final Tooling & Cleanup
**Files:** `pyproject.toml`, `.github/workflows/test.yml`, `scripts/update-assets.sh`
**Action:**
1.  **Linting:** Configure `ruff` and `mypy`. Add linting/formatting step to CI.
2.  **Coverage:** Add coverage threshold enforcement (80%) to CI.
3.  **Assets:** Create `scripts/update-assets.sh` to automate updates for `marked.js` and `Prism.js` from CDNs.

---

## WAVE 5: Advanced Features (Optional/Deferred)

1.  **S3 Storage:** Implement storage abstraction layer for optional S3-compatible media storage.
2.  **Page View Buffer:** Implement in-memory buffer for batching page view writes (for high-traffic sites).
3.  **Backup Encryption:** Add GPG encryption support for database backups.

---

## Testing Strategy
- **Unit Tests:** After each WAVE, run `python3 -m pytest tests/ --ignore=tests/e2e -v`.
- **Manual Verification:** Verify JS initialization in browser, check rate limiting with `curl`, and inspect FTS5 index consistency.
- **CI/CD:** Ensure all changes pass the new linting and coverage checks.
