# Blog Application Improvement Plan

Consolidated plan from code review. Items organized by priority.

**Excluded:** Rate limiting (handled by reverse proxy/WAF), HTTPS redirect (handled by reverse proxy), GET→POST migration for confirm/unsubscribe (breaking change for email links), separate unsubscribe tokens (breaking change for existing subscribers).

---

## Phase 1: Critical Security Fixes

### 1.1 CSRF on Logout

**Problem:** Logout uses `GET /admin/logout` (`admin.py:107`), allowing session termination via CSRF (e.g., `<img src="/admin/logout">`).

**Solution:** Change to POST with CSRF token.

- `app/routes/admin.py:107` — change `@admin.route("/logout")` to `@admin.route("/logout", methods=["POST"])`
- `app/templates/admin/dashboard.html` — change logout link to POST form with `csrf_token`
- `app/templates/base.html` — same if logout link exists there

### 1.2 Premature File Deletion on Rollback

**Problem:** In `edit_post()` (`admin.py:277-281`) and `bulk_operations()` (`admin.py:744-749`), image files are deleted before `db.session.commit()`. If commit fails and rolls back, the database references missing files.

**Solution:** Delete image files only after successful commit.

- `app/routes/admin.py` (`edit_post`, lines 275-310) — store old image filename, commit first, then delete file after successful commit. Wrap deletion in `try/except FileNotFoundError`.
- `app/routes/admin.py` (`bulk_operations`, lines 743-751) — collect image paths, commit, then delete files in a separate loop.

### 1.3 CSP Inline Style Blocking

**Problem:** CSP header `style-src 'self'` (`__init__.py:163`) blocks inline `style` attributes used in public templates (e.g., `--delay` CSS custom properties in `index.html:15`, `tag.html:14`, `search.html:21`) and admin templates (`editor.html:9`, `dashboard.html:7`, `analytics.html:48`, `media.html:36`).

**Solution:** Add `'unsafe-inline'` to `style-src` directive. Long-term goal: refactor inline styles to CSS classes.

- `app/__init__.py:163` — change to `style-src 'self' 'unsafe-inline';`
- `app/templates/admin/editor.html`, `dashboard.html`, `media.html`, `analytics.html` — extract common inline styles to CSS utility classes (`.flex-row`, `.gap-sm`, `.gap-md`, etc.) in `style.css`
- `app/static/css/style.css` — add utility classes

---

## Phase 2: Security Hardening

### 2.1 Subscriber Enumeration Fix

**Problem:** The subscribe endpoint (`public.py:180-227`) reveals whether an email exists: "You're already subscribed." vs "Check your inbox to confirm your subscription."

**Solution:** Return a unified message regardless of subscriber state.

- `app/routes/public.py:202-203` — change `flash("You're already subscribed.", "success")` to `flash("Check your inbox to confirm your subscription.", "success")`
- Internal log messages should still differentiate for debugging

### 2.2 Referrer Logging Sanitization

**Problem:** Full referrer URLs logged to database (`public.py:69`). Could contain sensitive query parameters (tokens, search terms).

**Solution:** Strip query parameters, keep only origin/path.

- `app/routes/public.py:69` — parse `request.referrer` with `urllib.parse.urlparse`, reconstruct without query string, truncate to 512 chars
- Apply same sanitization to any other referrer logging

### 2.3 Open Redirect via request.referrer

**Problem:** After subscription, redirect uses `request.referrer or "/"` (`public.py:185,214,227`). Attacker can spoof Referer header to redirect users to external sites.

**Solution:** Validate referrer host matches `request.host`, or hardcode redirect URL.

- `app/routes/public.py` (`subscribe`) — parse `request.referrer`, check `urlparse(referrer).netloc == request.host` (or empty for same-origin). Fall back to `url_for("public.index")` if mismatch.
- Apply to all three redirect locations in `subscribe()`: lines 185, 214, 227

### 2.4 Input Validation

**Problem:** Several routes lack input validation — unvalidated types, missing length limits.

- `app/routes/public.py` (`track_share`, ~line 164) — convert `post_id` to `int()`, handle `ValueError` with 400; truncate `platform` to 32 chars
- `app/routes/public.py` (`subscribe`, line 182) — truncate email to 256 chars (already `.strip().lower()`)
- `app/routes/admin.py` (`bulk_operations`) — validate each `post_id` is integer, handle `ValueError`
- `app/routes/admin.py` (create/edit post) — truncate title to 200, summary to 500 chars before saving

### 2.5 CSP connect-src Directive

**Problem:** CSP header doesn't specify `connect-src`, which defaults to `'self'`. Adding explicit directive improves clarity and prevents silent breakage if defaults change.

**Solution:** Add explicit `connect-src 'self'` to CSP.

- `app/__init__.py:161-168` — append `"connect-src 'self'; "` to CSP string

---

## Phase 3: Data Integrity

### 3.1 Newsletter Retry Loop & Per-Subscriber Tracking

**Problem:** When `send_newsletter()` returns `False` (SMTP failures), posts are retried every day forever with no retry limit. No per-subscriber tracking — partial sends could result in duplicates on retry.

**Solution:** Add `newsletter_attempts` column to `Post`. Skip after N failed attempts. Admin can reset via existing `/admin/newsletter-reset/<post_id>` route.

**Changes:**

- `app/models.py` — add `newsletter_attempts = db.Column(db.Integer, default=0, nullable=False)` after `newsletter_sent_at`
- `app/scheduler.py:29-36` — add `Post.newsletter_attempts < 5` to query filter
- `app/scheduler.py:50-54` — on success, reset `newsletter_attempts = 0` alongside `newsletter_sent_at`
- `app/scheduler.py:55-56` — on failure, increment `newsletter_attempts` per post
- `app/routes/admin.py` (`newsletter_reset`) — also reset `post.newsletter_attempts = 0`
- `app/templates/admin/dashboard.html` — update "Reset NL" button tooltip to show attempt count when > 0
- Migration: `flask db migrate -m "add newsletter_attempts to posts"` / `flask db upgrade`

**Tests:**
- Posts with `newsletter_attempts >= 5` are skipped
- Successful send resets attempts to 0
- Failure increments attempts
- SMTP disconnect mid-batch does not mark posts as sent

### 3.2 Subscriber expires_at Default Mismatch

**Problem:** `Subscriber.expires_at` model default is 365 days (`models.py:104`), but `subscribe()` route overrides to `CONFIRMATION_EXPIRY_HOURS` (default 1 hour). Model default is misleading — new subscribers created outside the route get a 365-day window.

**Solution:** Remove the model default; require explicit `expires_at` assignment.

- `app/models.py:104` — remove `default=lambda: utc_now() + timedelta(days=365)` from `expires_at`. Keep `nullable=True`.
- `app/routes/public.py` (`subscribe`) — already sets `expires_at` explicitly on all paths. No changes needed.
- `app/scheduler.py` (`cleanup_expired_subscribers`) — already filters `Subscriber.expires_at != None` before comparing. No changes needed.

### 3.3 IntegrityError Loop in edit_post()

**Problem:** After rollback in `edit_post()` (`admin.py:292-310`), all fields are re-applied. Per the IntegrityError rollback gotcha in AGENTS.md: `db.session.rollback()` expires all attributes. If another error occurs during retry, original data is lost.

**Solution:** Use `db.session.begin_nested()` (savepoint) before the outer commit, or fetch fresh object after rollback and only update slug.

- `app/routes/admin.py:290-310` — wrap in nested transaction. On `IntegrityError`, rollback to savepoint, regenerate slug only, retry commit.

---

## Phase 4: Performance

### 4.1 Database Index Optimization

**Problem:** Missing indexes cause full table scans; redundant indexes waste storage.

**Add:**
- `Post.newsletter_sent_at` — index for newsletter query filter (`scheduler.py:33`)
- `Subscriber` composite index on `(confirmed, unsubscribed_at)` — for newsletter subscriber query (`scheduler.py:42-44`)
- `Post` composite index on `(published, updated_at)` — if used for ordering

**Remove (redundant):**
- `Index('ix_posts_slug', 'slug')` — unique constraint already creates an index
- `Index('ix_share_events_post_id', 'post_id')` — covered by composite `ix_share_events_post_created`

**Changes:**
- `app/models.py` — add/remove index definitions
- Migration: `flask db migrate -m "optimize database indexes"` / `flask db upgrade`

### 4.2 setup.sh Directory Path Fix

**Problem:** `setup.sh:75` creates `static/uploads` relative to project root, but the app expects uploads at `app/static/uploads/`.

**Solution:**
- `setup.sh:75` — change to `mkdir -p instance logs app/static/uploads`

### 4.3 base62 O(1) Decode Lookup

**Problem:** `ALPHABET.index(char)` in `app/base62.py` is O(n). Negligible for 62 chars but unclean.

**Solution:**
- `app/base62.py` — add `_DECODE_MAP = {c: i for i, c in enumerate(ALPHABET)}`, use in decode function

---

## Phase 5: Code Quality & Cleanup

### 5.1 Remove Legacy Session Timestamp Parsing

**Problem:** `app/__init__.py:~134-150` handles old ISO string format for `last_activity` (backward compat). All sessions should now use float timestamps.

**Solution:** Remove legacy ISO string parsing code, simplify to float-only comparison.

### 5.2 Move Inline Template Imports to Top-Level

**Problem:** `render_template` is imported inside error handlers (`__init__.py:~78,83,89`) instead of at top of file.

**Solution:** Move `from flask import render_template` to top-level imports in `create_app()`.

### 5.3 Update Legacy SQLAlchemy API

**Problem:** `User.query.first()` in admin user creation uses legacy API.

**Solution:**
- `app/__init__.py` (`create_admin_user`) — change to `db.session.execute(db.select(User)).scalar_one_or_none()`

### 5.4 Tag Cache Double-Checked Locking Comment

**Problem:** The double-checked locking pattern in `_get_tag_counts()` (`cache.py`) releases lock, queries DB, then re-acquires. Between releases, another thread could populate the cache, wasting the DB query.

**Solution:** No code change needed — current implementation is correct (second check under lock ensures correctness). Add comment explaining the tradeoff.

- `app/cache.py` — add comment before DB query section explaining the pattern

### 5.5 Missing `__init__.py` in Migrations Folder

**Problem:** The `migrations/` folder lacks an `__init__.py` file, which is non-standard.

**Solution:**
- Create `migrations/__init__.py` as an empty file

### 5.6 backup.py --keep 0 Guard

**Problem:** `--keep 0` is allowed, deleting all backups immediately after creation.

**Solution:**
- `backup.py:~122` — add `if args.keep < 1: parser.error("--keep must be at least 1")`

### 5.7 Magic Numbers to Config

**Problem:** Various magic numbers throughout code (tag cache TTL, etc.) should be configurable.

**Solution:** Add to `config.toml [app]` section and load in `config.py`.

- Identify all magic numbers suitable for configuration (tag cache TTL, newsletter retry limit, etc.)
- Add to `config.toml` with appropriate defaults
- Update code to use config values

---

## Phase 6: UX & Accessibility

### 6.1 Accessibility Improvements

- `app/templates/_sidebar.html` — add `aria-label="Email address"` to email input
- `app/templates/base.html` — reduce skip links to one (main content); add `rel="noopener"` to all `target="_blank"` links
- `app/templates/admin/editor.html` — add `rel="noopener"` to preview and view post links

### 6.2 Search Page Broken Sidebar

**Problem:** Search template includes `{% include "_sidebar.html" %}` (`search.html:62`) but doesn't pass required `tags` and `tag_counts` variables. Sidebar is broken/empty on search results page.

**Solution:**
- `app/routes/public.py` (search route) — add `tags = Tag.query.order_by(Tag.name).all()` and `tag_counts = _get_tag_counts()` to template context

---

## Phase 7: Testing

### 7.1 Expanded Test Coverage

**New test files:**
- `tests/test_cache.py` — tag count cache, double-checked locking, invalidation
- `tests/test_csrf.py` — CSRF token generation and validation
- `tests/test_base62.py` — encode/decode round-trip, edge cases
- `tests/test_utils.py` — email validation, XML escaping, slug generation
- `tests/test_scheduler.py` — newsletter job, file locking, duplicate prevention

**Expand existing:**
- `tests/test_newsletter.py` — SMTP disconnect mid-batch, partial failure, retry logic
- `tests/test_admin.py` — preview endpoint, subscriber list, orphan tag cleanup, bulk operations with image cleanup, session timeout
- `tests/test_public.py` — RSS ordering, media gallery pagination, subscriber enumeration (unified response), subscriber expiration
- `tests/test_security.py` — CSP assertions (connect-src, style-src), token enumeration timing

---

## Phase 8: Future / Low Priority

- **Timezone-aware datetimes** — `utc_now()` returns naive datetime for SQLite compat. Migrate to aware datetimes if moving to PostgreSQL.
- **Search performance** — LIKE queries on body could be slow at scale. Consider full-text search or limiting body search to first N characters.
- **Multi-admin support** — Currently single admin user. Add `is_admin` field to User model, admin creation command.
- **Backup/restore UI** — Admin UI for manual backup trigger, automatic scheduled backups.
- **Subscriber expiry timezone** — All datetime comparisons use naive datetimes (consistent but anti-pattern).

---

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Run after each phase. Maintain 78%+ coverage.

---

## Migration Summary

1. `flask db migrate -m "add newsletter_attempts to posts"`
2. `flask db migrate -m "optimize database indexes"`
3. `flask db upgrade`

Run all migrations after completing Phases 1-3.
