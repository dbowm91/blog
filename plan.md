# Consolidated Improvement Plan

**Test Command (run after each change):**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Wave 1: Critical Bugs & Security

Items that affect correctness, security, or data integrity. Can be parallelized across two sub-waves.

### Wave 1A — Backend Critical (parallelizable)

#### 1.1 Fix `busy_timeout` PRAGMA for Connection Pooling
- **Priority:** Critical
- **Files:** `app/__init__.py`
- **Problem:** `PRAGMA busy_timeout=5000` is executed once during `create_app()` inside `with app.app_context()`. This is a **connection-level** setting in SQLite — it does NOT persist across connections. New pooled connections use the default `busy_timeout=0`, causing immediate `database is locked` errors under write contention.
- **Fix:** Use `@event.listens_for(Engine, "connect")` to apply `PRAGMA busy_timeout=5000` (and `PRAGMA journal_mode=WAL` for clarity) on every new connection. Remove the current `with app.app_context(): db.session.execute(text("PRAGMA ..."))` block.
- **Test:** Verify `PRAGMA busy_timeout` returns 5000 after pool checkout. Simulate concurrent writes.

#### 1.2 Align `MAX_CONTENT_LENGTH` with `MAX_UPLOAD_SIZE`
- **Priority:** Critical
- **Files:** `app/__init__.py`
- **Problem:** `MAX_CONTENT_LENGTH` is hardcoded to 16MB (`app/__init__.py:69`) but `_save_image()` enforces 10MB from config. The 413 error handler says "Maximum upload size is 16MB" — misleading since the app only accepts 10MB.
- **Fix:** Import `MAX_UPLOAD_SIZE` from `app.config` and set `MAX_CONTENT_LENGTH` to `MAX_UPLOAD_SIZE + buffer` (e.g., 1MB for form data overhead). Update the 413 handler message to reference the config value.
- **Test:** Upload files at boundary sizes (9MB, 10MB, 11MB) to verify correct error messages.

#### 1.3 Fix Newsletter SMTP Reconnection Cleanup
- **Priority:** Critical
- **Files:** `app/email.py`
- **Problem:** In `send_newsletter()`, when `SMTPServerDisconnected` is caught, `server.quit()` is called before reconnection. While wrapped in try/except, this is redundant and the pattern is fragile. The `finally` block also calls `server.quit()`.
- **Fix:** Remove `server.quit()` from the except handler — let the `finally` block handle cleanup. On reconnect failure, log and abort the newsletter batch rather than silently continuing.
- **Test:** Mock `SMTPServerDisconnected` mid-batch and verify no error on cleanup. Verify reconnection succeeds.

#### 1.4 Add Bounds to In-Memory Caches
- **Priority:** Critical
- **Files:** `app/cache.py`, `app/routes/admin.py`
- **Problem:** `_TAG_COUNTS_CACHE` stores a single entry (no size issue), but `_analytics_cache` in admin.py is an unbounded dict keyed by `days` parameter. Over time, if many different `days` values are queried, the dict grows without limit.
- **Fix:** Add `_ANALYTICS_MAX_SIZE = 16` to analytics cache. On write, if size exceeds max, evict oldest entry (LRU). Document that multi-worker deployments should use external caching.
- **Test:** Verify cache expires after TTL and doesn't grow beyond max size.

### Wave 1B — Frontend Critical (parallelizable with 1A)

#### 1.5 Remove Hardcoded Year in Context Processor
- **Priority:** Medium
- **Files:** `app/__init__.py`
- **Problem:** `inject_config()` context processor returns `"current_year": 2026` hardcoded. Footer copyright year will be wrong starting January 1st of the next year.
- **Fix:** Replace with `datetime.now().year`. The `inject_footer_data()` function already imports `datetime` — reuse that import or import inside `inject_config`.
- **Test:** None needed — trivial change.

#### 1.6 Remove Redundant `ConnectionError` Exception Catch
- **Priority:** Low
- **Files:** `app/routes/public.py`
- **Problem:** `_try_send_confirmation()` catches `ConnectionError` separately in `except (smtplib.SMTPException, ConnectionError, OSError)`, but `ConnectionError` is a subclass of `OSError`, which is already caught. Dead code.
- **Fix:** Remove `ConnectionError` from the except tuple: `except (smtplib.SMTPException, OSError)`.
- **Test:** Existing tests should pass.

#### 1.7 Fix Missing CSP Nonce on Dashboard Inline Script
- **Priority:** Critical
- **Files:** `app/templates/admin/dashboard.html`, `app/static/js/main.js`
- **Problem:** The bulk actions JavaScript is inline without `nonce="{{ csp_nonce }}"`. CSP will block it in production.
- **Fix:** Move the inline script logic (dashboard.html lines 142-170) into `main.js`. Extend the existing `#select-all` handler (lines 440-448) to also toggle `bulk-actions` visibility and update `bulk-progress-bar`. Remove the entire inline `<script>` block from dashboard.html.
- **Test:** Run with `CSRF_ENABLED=False TESTING=True` config. Verify bulk actions work.

---

## Wave 2: High-Priority UX & Accessibility

### Wave 2A — Backend/Route Fixes (parallelizable)

#### 2.1 Strengthen Tag Name Validation
- **Priority:** High
- **Files:** `app/routes/admin.py`, `app/templates/admin/tags.html`, `tests/test_admin.py`
- **Problem:** `TAG_NAME_REGEX` uses `^[\w\s-]+$` which allows many Unicode word characters. Too permissive for URLs.
- **Fix:** Restrict to ASCII letters, digits, spaces, and hyphens: `^[a-zA-Z0-9\s\-]+$`. Add max length validation (50 chars). Update error message. Add help text in tags.html.
- **Test:** Test invalid tag names (Unicode, special chars, too long).

#### 2.2 Remove Dead `_csrf_exempt` Check
- **Priority:** Medium
- **Files:** `app/__init__.py`
- **Problem:** `validate_csrf_token()` checks for `_csrf_exempt` attribute on view functions, but no route sets it. Dead code creates confusion about CSRF protection scope.
- **Fix:** Remove the `_csrf_exempt` check from `validate_csrf_token()`. Update AGENTS.md to note that CSRF exemption is not supported (use proxy-level bypass if needed).
- **Test:** Existing tests should pass.

#### 2.3 Fix Analytics Cache Global State in Tests
- **Priority:** Medium
- **Files:** `tests/conftest.py`, `app/routes/admin.py`
- **Problem:** `_analytics_cache` persists across test runs, causing flaky tests and cross-test pollution.
- **Fix:** Add `_analytics_cache.clear()` to a fixture in `conftest.py` applied to admin tests that touch analytics.
- **Test:** Run analytics-related tests in isolation and in sequence — no cross-test pollution.

### Wave 2B — Frontend UX (parallelizable with 2A)

#### 2.4 Move Select-All Checkbox Outside Hidden Bulk Actions Bar
- **Priority:** High
- **Files:** `app/templates/admin/dashboard.html`
- **Problem:** The `#select-all` checkbox is inside the hidden `#bulk-actions` div. Users cannot "select all" without first manually checking one post.
- **Fix:** Move the `<input type="checkbox" id="select-all" form="bulk-form">` from inside `#bulk-actions` to the `.filter-bar` section, next to the search input and status filter. The `form="bulk-form"` attribute already correctly associates it with the form.
- **Test:** Verify select-all works without checking any post first.

#### 2.5 Fix Tag Page Hero Layout
- **Priority:** High
- **Files:** `app/templates/tag.html`
- **Problem:** The tag hero (`<h1>`) appears inside the `content-layout` grid, placing it next to the sidebar instead of spanning the full page width above the grid.
- **Fix:** Move the `<div class="tag-hero animate-in">` block outside and before the `<div class="content-layout">`. The breadcrumb is already outside the grid, so the tag hero should go between the breadcrumb and the content-layout div.
- **Test:** Verify at desktop and mobile breakpoints.

#### 2.6 Add Modal Focus Trapping
- **Priority:** Medium
- **Files:** `app/static/js/main.js`
- **Problem:** The keyboard shortcuts modal does not trap focus. Users can tab out of the modal into the background page.
- **Fix:** Implement focus trapping when the modal is open. On open, store the previously focused element. On Tab/Shift+Tab, cycle focus within the modal. On close, restore focus to the stored element.
- **Test:** Manual browser testing or headless browser test.

#### 2.7 Add Unsaved Changes Warning in Editor
- **Priority:** Medium
- **Files:** `app/static/js/main.js`
- **Problem:** Navigating away from the editor without submitting loses any changes not yet autosaved to localStorage.
- **Fix:** Add a `beforeunload` event listener when the editor has unsaved changes. Track "dirty" state by comparing current form values against the last saved draft in localStorage. Remove the listener on successful form submit.
- **Test:** Manual verification — navigate away after editing, confirm browser dialog appears.

#### 2.8 Scope Reading Progress Bar to Post Pages
- **Priority:** Low
- **Files:** `app/templates/base.html`, `app/templates/post.html`
- **Problem:** The `.reading-progress` div exists on all public pages but only makes sense on article pages. Currently non-functional (no JS drives it).
- **Fix:** Move the `<div class="reading-progress">` from base.html to post.html. If JS for the progress bar is added later, it will only render where relevant.
- **Test:** Verify reading progress bar only appears on post pages.

---

## Wave 3: UI Polish & Consistency

### Wave 3A — CSS & Visual (parallelizable)

#### 3.1 Replace Emoji Content with SVG Icons
- **Priority:** Medium
- **Files:** `app/static/css/style.css`
- **Problem:** CSS uses `content: "📭"` for empty states and `content: "⚠ "` for form errors. Emojis render inconsistently across platforms and contradict the self-hosted asset philosophy.
- **Fix:** Replace `content` emoji values with inline SVG `background-image` on the pseudo-elements. Use data URI SVGs for mailbox (empty state) and warning triangle (form error).
- **Test:** Verify in both dark and light modes.

#### 3.2 Standardize CSS Variable Usage
- **Priority:** Medium
- **Files:** `app/static/css/style.css`
- **Problem:** Many rules use hardcoded pixel values instead of CSS variables.
- **Fix:** Add `--radius-sm: 6px` and `--space-md-sm: 12px` to `:root` and `[data-theme="light"]`. Systematically replace hardcoded values:
  - `border-radius: 8px` → `var(--radius)`
  - `border-radius: 12px` → `var(--radius-lg)`
  - `border-radius: 6px` → `var(--radius-sm)`
  - `gap: 16px` → `var(--space-md)`
  - `gap: 48px` → `var(--space-2xl)`
  - `gap: 24px` → `var(--space-lg)`
  - `gap: 12px` → `var(--space-md-sm)`
  - `padding: 24px` → `var(--space-lg)`
  - `padding: 16px` → `var(--space-md)`
- **Caveat:** Leave `prism-okaidia.css` alone (third-party theme).
- **Test:** Visual verification in both dark and light modes.

#### 3.3 Add Accent Borders to Analytics Stat Cards
- **Priority:** Low
- **Files:** `app/templates/admin/analytics.html`, `app/static/css/style.css`
- **Problem:** Dashboard stat cards have colored left borders but analytics stat cards do not.
- **Fix:** Add accent border classes to the 4 stat cards in analytics.html. Map semantically: Page Views → `stat-card-accent-views`, Total Subscribers → `stat-card-accent-subscribers`, Confirmed → `stat-card-accent-posts`, Posts Viewed → `stat-card-accent-shares`.
- **Test:** Visual verification.

#### 3.4 Improve Text-Dim Contrast at Small Sizes
- **Priority:** Low
- **Files:** `app/static/css/style.css`
- **Problem:** `--text-dim` at small sizes (0.7rem tag counts, 0.6rem chart labels) may not meet WCAG AA 4.5:1 contrast ratio, especially in light mode (~3.1:1 on `#f6f8fa`).
- **Fix:** Add `--text-dim-strong: #9ca3af` (dark) and `--text-dim-strong: #4b5563` (light) for small text. Update `.tag-count`, `.chart-label`, and other small text to use it. These values provide ~6.5:1 (dark) and ~7.4:1 (light) contrast ratios.
- **Test:** Visual verification in both modes.

#### 3.5 Fix Search Input Focus Layout Shift
- **Priority:** Low
- **Files:** `app/static/css/style.css`
- **Problem:** Search input expands from 200px to 260px on focus, causing layout shift on mobile.
- **Fix:** Cap the expansion: `width: 240px` on focus. On mobile (`max-width: 768px`), use `width: calc(100% - 80px)` to remove expansion.
- **Test:** Verify no layout shift on mobile.

#### 3.6 Improve Share Button Visual Hierarchy
- **Priority:** Low
- **Files:** `app/static/css/style.css`
- **Problem:** Share buttons are plain and only show color on hover.
- **Fix:** Add subtle background colors matching brand colors:
  - `.share-twitter { background: rgba(29, 161, 242, 0.1); }`
  - `.share-linkedin { background: rgba(10, 102, 194, 0.1); }`
  - `.share-hn { background: rgba(255, 102, 0, 0.1); }`
  - `.share-reddit { background: rgba(255, 69, 0, 0.1); }`
  - `.share-facebook { background: rgba(24, 119, 242, 0.1); }`
- **Test:** Visual verification.

### Wave 3B — Template & Content (parallelizable with 3A)

#### 3.7 Standardize Empty State Messaging
- **Priority:** Medium
- **Files:** `app/templates/index.html`
- **Problem:** `index.html` says "No posts yet. Something is brewing..." while `dashboard.html` says "No posts yet. Create your first one."
- **Fix:** Update `index.html:39` to match dashboard: "No posts yet. Create your first one."
- **Test:** Visual verification.

#### 3.8 Add Meta Description to Tag and Search Pages
- **Priority:** Low
- **Files:** `app/templates/tag.html`, `app/templates/search.html`
- **Problem:** Post pages have meta description, but tag and search pages don't.
- **Fix:** Add `{% block meta_description %}` to:
  - `tag.html`: `Posts tagged with {{ tag.name }}`
  - `search.html`: `Search results for {{ query }}`
- **Test:** View page source to verify meta description.

#### 3.9 Enable Image Loading Skeleton
- **Priority:** Medium
- **Files:** `app/templates/index.html`, `app/templates/post.html`, `app/templates/_sidebar.html`
- **Problem:** The `.img-skeleton` CSS exists but is never actively used.
- **Fix:** Add `.img-skeleton` class to lazy-loaded images: `<img class="post-card-img img-skeleton" ...>`.
- **Test:** Verify skeleton animation appears before images load.

#### 3.10 Add Keyboard Navigation to Post Cards
- **Priority:** Medium
- **Files:** `app/templates/index.html`, `app/templates/tag.html`, `app/templates/search.html`, `app/static/js/main.js`, `app/static/css/style.css`
- **Problem:** Post cards are not keyboard-navigable.
- **Fix:** Add `tabindex="0" role="link"` to post cards. Add keydown handler for Enter/Space to click the card's link. Add `.post-card:focus-visible` CSS with outline.
- **Test:** Tab through page, verify cards are focusable and activatable.

#### 3.11 Add Loading Indicator on Auto-Submit Filters
- **Priority:** Low
- **Files:** `app/static/js/main.js`, `app/static/css/style.css`
- **Problem:** Status filter and date range filter auto-submit on change with no visual feedback.
- **Fix:** Add a `.loading` class before submit — reduced opacity + wait cursor. Since the page navigates away immediately, the visual cue only needs to last ~100-200ms.
- **Test:** Verify visual feedback on filter change.

### Wave 3C — Admin Enhancements (parallelizable with 3A and 3B)

#### 3.12 Add Bulk Form Submission Loading State
- **Priority:** Medium
- **Files:** `app/static/js/main.js`, `app/static/css/style.css`, `app/templates/admin/dashboard.html`
- **Problem:** Bulk operations submit via standard form POST, providing no visual feedback during the request.
- **Fix:** Add a hidden loading overlay that shows during bulk form submission. Use `beforeunload` event to show overlay when form is submitted. Hide overlay on page load.
- **Test:** Submit bulk operation, verify loading overlay appears.

#### 3.13 Add Footer to Admin Pages
- **Priority:** Low
- **Files:** `app/templates/admin/base.html`, `app/static/css/style.css`
- **Problem:** Admin pages end abruptly after content — no footer.
- **Fix:** Add a lightweight admin footer with links: View Site, RSS Feed, copyright. Add `.admin-footer` CSS.
- **Test:** Verify footer appears on all admin pages.

#### 3.14 Add Stat Card Trend Indicators
- **Priority:** Medium
- **Files:** `app/routes/admin.py`, `app/templates/admin/dashboard.html`
- **Problem:** The `.stat-trend` class exists in CSS but isn't used. Stat cards could show week-over-week comparison.
- **Fix:** In `dashboard()` route, calculate week-over-week view comparison. Pass `views_trend` to template. Add `<span class="stat-trend">` to stat cards.
- **Test:** Verify trend data displays correctly.

---

## Wave 4: Testing & Documentation

### Wave 4A — New Tests (parallelizable)

#### 4.1 Add Backup/Restore End-to-End Tests
- **Priority:** High
- **Files:** `tests/test_backup.py` (create)
- **Tasks:** Test backup creation (compressed/uncompressed), file listing, download, filename validation, restore, restore with corrupted backup, backup while DB in use.

#### 4.2 Add Multi-User Session Management Tests
- **Priority:** High
- **Files:** `tests/test_multi_user.py` (create)
- **Tasks:** Test two users logging in simultaneously, session timeout on one user while other remains active, `AdminSession` cleanup on logout, session cookie security flags.

#### 4.3 Expand Search Special Character Tests
- **Priority:** Medium
- **Files:** `tests/test_public.py`
- **Tasks:** Add tests for comma, semicolon, pipe, backslash, Unicode, empty search, very long search query (>200 chars).

#### 4.4 Add Email Failure/Retry Tests
- **Priority:** Medium
- **Files:** `tests/test_email.py`, `tests/test_newsletter.py`
- **Tasks:** Test newsletter sending with SMTP failure, reconnection after disconnect, confirmation email send failure, attempt counting, mixed success/failure in batch.

### Wave 4B — Documentation (parallelizable with 4A)

#### 4.5 Document Multi-Worker Scheduler Limitation
- **Priority:** Medium
- **Files:** `app/scheduler.py`, `DEPLOY.md`
- **Problem:** APScheduler runs in-process. With multiple workers, each runs its own scheduler. The `fcntl` file lock prevents duplicate sends on a single machine but doesn't help across machines.
- **Fix:** Document the limitation clearly. Recommend single-worker deployment for newsletter scheduling, or external scheduler (cron, Celery beat).

#### 4.6 Improve Backup Path Resolution
- **Priority:** Low
- **Files:** `backup.py`
- **Problem:** `get_db_path()` returns `"instance/blog.db"` relative to CWD, not `app.instance_path`.
- **Fix:** Add `--db` CLI argument for explicit path. Fall back to `"instance/blog.db"` for backward compatibility.

---

## Wave 5: Split admin.py (Large Refactor)

#### 5.1 Split `admin.py` into Route Modules
- **Priority:** Medium
- **Effort:** Large
- **Files:** `app/routes/admin.py` → `app/routes/admin/` package
- **Problem:** `admin.py` is 1556 lines. Hard to navigate, increases merge conflicts.
- **Fix:** Convert to package:
  - `app/routes/admin/__init__.py` — Blueprint registration, `admin_required`, shared helpers
  - `app/routes/admin/auth.py` — login, logout
  - `app/routes/admin/posts.py` — dashboard, new_post, edit_post, delete_post, bulk_operations, preview
  - `app/routes/admin/subscribers.py` — subscribers, delete, export, bulk
  - `app/routes/admin/tags.py` — tags_list, create, rename, delete
  - `app/routes/admin/users.py` — users_list, create, delete, change_password
  - `app/routes/admin/sessions.py` — sessions_list, revoke_session
  - `app/routes/admin/media.py` — media, upload, delete
  - `app/routes/admin/backup.py` — backup CRUD
  - `app/routes/admin/analytics.py` — analytics
  - `app/routes/admin/newsletter.py` — newsletter_test
- **Shared helpers** (`_save_image`, `_detect_image_type`, `_generate_unique_slug`, `_get_posts_query`, `_get_analytics_data`, `_cleanup_orphan_tags`, `_get_or_create_tags`, `_apply_post_updates`, `_categorize_referrer`, `_check_password_complexity`, `_get_backup_dir`) stay in `__init__.py` or a new `helpers.py`.
- **Test:** Full test suite must pass. Verify all admin routes still work.

---

## Deferred / Explicitly Not Doing

| Item | Reason |
|------|--------|
| Password hashing migration (Argon2/bcrypt) | Current PBKDF2 is acceptable for this use case |
| Application-level rate limiting | Explicitly rejected — handled by reverse proxy (see AGENTS.md) |
| Celery/Redis distributed task queue | Major architectural change; overkill for single-worker blog |
| Redis-backed sessions | Adds infrastructure dependency unnecessarily |
| Architecture Decision Records (ADRs) | Design decisions already documented in AGENTS.md |
| Full type hints across codebase | Good hygiene but not critical; can be done incrementally |
| `__all__` exports | Minor; wildcard imports shouldn't be used anyway |
| `db.engine.dispose()` on shutdown | OS cleans up SQLite file handles on process exit |
| FTS5 full special character escaping | Current quote-wrapping + LIKE fallback handles most cases |
| CSV export robustness improvements | Current implementation sufficient for real-world data |
| localStorage quota handling for drafts | Edge case (5-10MB quota); can add if users report issues |
| Newsletter fake subscriber improvement | Works but brittle; low priority |

---

## Implementation Order Summary

| Wave | Description | Parallelizable? |
|------|-------------|-----------------|
| **1A** | Backend critical (busy_timeout, upload size, SMTP, caches, hardcoded year, redundant exception) | Yes — 6 sub-agents |
| **1B** | Frontend critical (CSP nonce) | Yes — runs parallel to 1A |
| **2A** | Backend/Route fixes (tag validation, csrf_exempt, test cache) | Yes — 3 sub-agents |
| **2B** | Frontend UX (select-all, tag hero, modal focus, editor warning, reading progress) | Yes — 5 sub-agents |
| **3A** | CSS & Visual (emoji→SVG, CSS vars, accent borders, contrast, search shift, share buttons) | Yes — 6 sub-agents |
| **3B** | Template & Content (empty state, meta desc, image skeleton, keyboard nav, filter loading) | Yes — 5 sub-agents |
| **3C** | Admin Enhancements (bulk loading, admin footer, trend indicators) | Yes — 3 sub-agents |
| **4A** | New Tests (backup, multi-user, search, email) | Yes — 4 sub-agents |
| **4B** | Documentation (scheduler docs, backup path) | Yes — 2 sub-agents |
| **5** | Split admin.py (large refactor) | No — do last to avoid conflicts |

**Waves 1–4 can be executed in parallel within each wave. Wave 5 must be done last.**
