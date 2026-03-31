# Blog Application Improvement Plan

Consolidated plan from code review. Items organized by priority.

**Excluded:** Rate limiting (handled by reverse proxy/WAF), HTTPS redirect (handled by reverse proxy), GET→POST migration for confirm/unsubscribe (breaking change for email links), separate unsubscribe tokens (breaking change for existing subscribers).

**Status:** Phases 1-8 complete. All 182 tests passing.

---

## Phase 1: Critical Security Fixes ✅

### 1.1 CSRF on Logout ✅

- `app/routes/admin.py` — changed to `@admin.route("/logout", methods=["POST"])`
- `app/templates/base.html` — logout link changed to POST form with `csrf_token`
- `app/templates/admin/base.html` — same
- `app/static/css/style.css` — added `.nav-link-btn` styling
- `tests/test_admin.py` — updated `test_logout` to use POST

### 1.2 Premature File Deletion on Rollback ✅

- `app/routes/admin.py` (`edit_post`) — old image filename stored before mutation, deleted only after successful commit
- `app/routes/admin.py` (`bulk_operations`) — image paths collected, batch committed, then files removed
- `app/routes/admin.py` (`delete_post`) — same fix applied (was also broken)

### 1.3 CSP Inline Style Blocking ✅

- `app/__init__.py` — changed to `style-src 'self' 'unsafe-inline'`
- `app/static/css/style.css` — added utility classes: `.flex-row`, `.gap-xs/sm/md`, `.items-center`, `.ml-auto`, `.mt-sm/md`, `.autosave-status-base`
- Templates updated: `editor.html`, `dashboard.html`, `media.html`
- Dynamic inline styles (animation delays, chart heights) remain inline

---

## Phase 2: Security Hardening ✅

### 2.1 Subscriber Enumeration Fix ✅

- `app/routes/public.py` — "already subscribed" now returns same message as new subscription
- Added `logger.info()` for debugging

### 2.2 Referrer Logging Sanitization ✅

- `app/routes/public.py` — referrer parsed with `urlparse`, query string stripped via `urlunparse`, truncated to 512 chars

### 2.3 Open Redirect via request.referrer ✅

- `app/routes/public.py` — added `_safe_redirect_url()` helper
- Validates `urlparse(referrer).netloc == request.host` (or empty for same-origin)
- Falls back to `url_for("public.index")` on mismatch
- Applied to all three redirect locations in `subscribe()`

### 2.4 Input Validation ✅

- `track_share` — validates `post_id` as `int()`, returns 400 on `ValueError`; truncates `platform` to 32 chars
- `subscribe` — email truncated to 256 chars
- `bulk_operations` — validates each `post_id` is integer
- `new_post` / `edit_post` — title truncated to 200, summary to 500 chars

### 2.5 CSP connect-src Directive ✅

- `app/__init__.py` — added `"connect-src 'self'; "` to CSP string

---

## Phase 3: Data Integrity ✅

### 3.1 Newsletter Retry Loop & Per-Subscriber Tracking ✅

- `app/models.py` — added `newsletter_attempts = db.Column(db.Integer, default=0, nullable=False)`
- `app/scheduler.py` — filter includes `Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS`; on success resets attempts to 0; on failure increments attempts
- `app/routes/admin.py` (`newsletter_reset`) — also resets `post.newsletter_attempts = 0`
- `app/templates/admin/dashboard.html` — tooltip shows attempt count when > 0
- `app/config.py` — added `NEWSLETTER_MAX_RETRY_ATTEMPTS` config
- `config.toml` — added `max_retry_attempts = 5`

### 3.2 Subscriber expires_at Default Mismatch ✅

- `app/models.py` — removed `default=lambda: utc_now() + timedelta(days=365)` from `expires_at`
- Removed unused `timedelta` import from models.py

### 3.3 IntegrityError Loop in edit_post() ✅

- `app/routes/admin.py` (`edit_post`) — simplified to only re-apply slug after rollback (slug collision is the only IntegrityError source)

---

## Phase 4: Performance ✅

### 4.1 Database Index Optimization ✅

- Added: `ix_posts_newsletter_sent_at`, `ix_posts_published_updated`, `ix_subscribers_confirmed_unsubscribed`
- Removed: `ix_posts_slug` (redundant with unique constraint), `ix_share_events_post_id` (covered by composite)
- Migration: `89a922eae517`

### 4.2 setup.sh Directory Path Fix ✅

- Changed to `mkdir -p instance logs app/static/uploads`

### 4.3 base62 O(1) Decode Lookup ✅

- Added `_DECODE_MAP = {c: i for i, c in enumerate(ALPHABET)}`

---

## Phase 5: Code Quality & Cleanup ✅

### 5.1 Remove Legacy Session Timestamp Parsing ✅

- Simplified to `float(last_activity)` with `try/except (ValueError, TypeError)` fallback

### 5.2 Move Inline Template Imports to Top-Level ✅

- Added `render_template, redirect, url_for, request as req, flash` to module-level imports

### 5.3 Update Legacy SQLAlchemy API ✅

- Changed `User.query.first()` to `db.session.execute(db.select(User)).scalar_one_or_none()`

### 5.4 Tag Cache Double-Checked Locking Comment ✅

- Added explanatory comments before DB query section

### 5.5 Missing `__init__.py` in Migrations Folder ✅

- Created `migrations/__init__.py`

### 5.6 backup.py --keep 0 Guard ✅

- Added `if args.keep < 1: parser.error("--keep must be at least 1")`

### 5.7 Magic Numbers to Config ✅

- Added `tag_cache_ttl_seconds = 60` to `config.toml [app]`
- Added `max_retry_attempts = 5` to `config.toml [newsletter]`
- `app/cache.py` — reads TTL from config via `_get_tag_ttl()`
- `app/scheduler.py` — reads retry limit from config

---

## Phase 6: UX & Accessibility ✅

### 6.1 Accessibility Improvements ✅

- `_sidebar.html` — added `aria-label="Email address"` to email input
- `base.html` — reduced skip links to one (main content)
- `editor.html` — added `rel="noopener"` to Preview and View Post links

### 6.2 Search Page Broken Sidebar ✅

- `app/routes/public.py` (search route) — passes `tags` and `tag_counts` to template

---

## Phase 7: Testing ✅

### 7.1 Expanded Test Coverage ✅

**New test files:**
- `tests/test_cache.py` — tag count cache, invalidation, TTL expiry, copy protection
- `tests/test_base62.py` — encode/decode round-trip, edge cases, decode map consistency
- `tests/test_utils.py` — email validation, XML escaping, slug generation

**Expanded existing:**
- `tests/test_newsletter.py` — retry logic, attempt tracking, reset clears attempts
- `tests/test_admin.py` — preview endpoint, bulk publish/delete, invalid post IDs, newsletter reset with attempts
- `tests/test_public.py` — subscriber enumeration unified response, open redirect prevention, track_share validation, referrer sanitization, search sidebar tags
- `tests/test_security.py` — CSP connect-src, style-src unsafe-inline, logout POST-only

**Not yet implemented:**
- `tests/test_csrf.py` — separate CSRF test file (covered by existing `test_csrf_protection`)
- `tests/test_scheduler.py` — scheduler-specific tests
- SMTP disconnect mid-batch tests, RSS ordering tests, session timeout tests

---

## Phase 8: Future / Low Priority ✅

### 8.1 Timezone-Aware Datetimes ✅

- `app/utils.py` — `utc_now()` now returns timezone-aware UTC datetime
- Added `UTCDateTime` TypeDecorator — stores naive UTC in SQLite, returns aware UTC on read
- All model DateTime columns updated: `Post.created_at/updated_at/published_at/newsletter_sent_at`, `Subscriber.created_at/expires_at/unsubscribed_at`, `PageView.created_at`, `ShareEvent.created_at`
- Existing naive rows auto-converted to aware on read (interpreted as UTC)
- `app/routes/public.py` — health check uses `utc_now().isoformat()` (includes timezone offset)

### 8.2 Search Performance (FTS5) ✅

- `app/search.py` — new module with `init_fts()`, `rebuild_fts()`, `sync_fts()`, `remove_fts()`
- `app/routes/public.py` — `_fts_search()` uses FTS5 MATCH with fallback to LIKE
- FTS5 index synced on post create/edit/delete and bulk operations
- LIKE fallback filters by `Post.published == True` (graceful degradation when FTS unavailable)
- FTS table check via `sqlite_master` before attempting MATCH query

### 8.3 Multi-Admin Support ✅

- `app/models.py` — `User.is_admin = db.Column(db.Boolean, default=False, nullable=False)`
- `app/__init__.py` — first user auto-promoted to admin; `flask create-admin` CLI command
- `app/routes/admin.py` — user management routes: list, create, delete, change password
- `app/templates/admin/users.html` — user management UI
- Safety: cannot delete own account, cannot delete last admin, min 8-char password
- `migrations/versions/1eed0a59a445_add_is_admin_to_users.py` — migration

### 8.4 Backup/Restore UI ✅

- `app/routes/admin.py` — backup routes: create, list, download, restore, delete
- `app/templates/admin/backup.html` — backup management UI
- Backups stored in `instance/backups/` directory
- Compressed backup support (gzip)
- Filename validation via `BACKUP_FILENAME_RE` regex (path traversal prevention)
- `download_backup` uses `send_file()` (no file handle leak)
- Restore copies backup over current DB (app restart required)
- Dashboard and nav links to Users and Backups pages

### 8.5 Subscriber Expiry Timezone ✅

- Handled by 8.1: `utc_now()` returns aware datetimes, `UTCDateTime` ensures all DB reads return aware
- All datetime comparisons (`expires_at < utc_now()`) now timezone-aware
- `CONFIRMATION_EXPIRY_HOURS` calculation produces aware datetimes

---

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

182 tests passing. Maintain 78%+ coverage.

---

## Migration Summary

1. `1992db4c5c98` — composite indexes and published_at index (fixed from broken original)
2. `89a922eae517` — newsletter_attempts, index optimization
3. `1eed0a59a445` — add is_admin to users

Run: `flask db upgrade`
