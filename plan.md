# Consolidated Improvement Plan

Created 2026-03-31. Merged from plan2.md, plan3.md, plan4.md, and plan5.md.
All items verified against current codebase.

---

## Wave 1: Bug Fixes (Critical — do first)

### 1.1: Fix missing `select` import in `create_admin` CLI command
- **File**: `app/__init__.py:219`
- **Problem**: `select(User)` is called but `select` is not imported from `sqlalchemy`. Raises `NameError` at runtime.
- **Fix**: Add `from sqlalchemy import select` to imports in `app/__init__.py`.

### 1.2: Improve FTS5 error logging
- **File**: `app/search.py`
- **Problem**: `sync_fts()` and `remove_fts()` log at `DEBUG` level (easy to miss). No exception objects included in any log message.
- **Fix**: Change `logger.debug` → `logger.warning` in `sync_fts()` and `remove_fts()`. Add `as e` to all four `except Exception` clauses and include `e` in log messages.

### 1.3: Backup restore should close DB connections before replacing file
- **File**: `app/routes/admin.py:951-967`
- **Problem**: `restore_backup()` copies a backup over the active DB while Flask-SQLAlchemy may have open connections. Can corrupt the database or cause stale file handle errors.
- **Fix**: Add `db.session.close_all(); db.engine.dispose()` before `shutil.copy2()`. Add flash message warning about potential restart.

### 1.4: `_cleanup_orphan_tags` should not commit independently
- **File**: `app/routes/admin.py:370-382`
- **Problem**: `_cleanup_orphan_tags()` calls `db.session.commit()` internally. If ever called within an outer transaction, the inner commit would prematurely flush unrelated changes.
- **Fix**: Remove the `db.session.commit()` from `_cleanup_orphan_tags()`. Callers already commit or have already committed. Add a comment noting callers are responsible.

### 1.5: `confirm` endpoint should handle already-confirmed subscribers
- **File**: `app/routes/public.py:312-330`
- **Problem**: If a confirmed subscriber clicks their confirm link again, the code sets `confirmed = True` (no-op) and commits — wastes a write and provides no user feedback.
- **Fix**: Add an early return if `sub.confirmed` is already `True` with flash message "Already confirmed."

---

## Wave 2: Test Migration & Coverage

### 2.1: Migrate legacy `.query` API in tests to SQLAlchemy 2.0
- **Files**: `tests/test_phase8.py`, `tests/test_admin.py`, `tests/test_public.py`, `tests/test_newsletter.py`
- **Problem**: 17 uses of `Model.query.filter_by(...)` across test files trigger `LegacyAPIWarning`.
- **Fix**: Replace all `Model.query.*` calls with `db.session.execute(select(Model).filter(...)).scalars().all()` and similar patterns. Import `select` from `sqlalchemy` where needed.

### 2.2: Fix `db.func.now()` in email tests
- **File**: `tests/test_email.py:21,46,74`
- **Problem**: Tests use `db.func.now()` for `published_at`, which returns SQLite's `CURRENT_TIMESTAMP` (naive). The app uses `utc_now()` (timezone-aware UTC).
- **Fix**: Replace `db.func.now()` with `utc_now()` imported from `app.utils`.

### 2.3: Fix `test_cannot_delete_last_admin` test assertion
- **File**: `tests/test_phase8.py:194`
- **Problem**: Test creates two admins, deletes the *other* admin, and only asserts `status_code == 200`. Does not verify the "last admin" guard actually works.
- **Fix**: Restructure: (1) delete user2 first (should succeed), (2) attempt to delete admin_user (the last admin), (3) assert deletion is blocked.

### 2.4: Add missing tests
- **Missing coverage**:
  - `/health` endpoint
  - `create-admin` CLI command
  - Image replacement in `edit_post()` (uploading new image when one exists)
  - `restore_backup` endpoint (path traversal protection, valid restore)
  - `confirm` endpoint with already-confirmed subscriber
  - `confirm` endpoint with expired token
  - `subscribe` with unsubscribed user re-subscribing
  - `newsletter_test` with custom `test_email` form field
  - Dashboard search (`?q=`) and status filter (`?status=`)
  - Bulk operations with invalid action
  - Image cleanup on edit/delete/bulk operations
  - FTS5 MATCH search path (ensure FTS table initialized, create post, `sync_fts()`, search)
  - Config validation error cases (invalid `send_time`, `posts_per_page`, `smtp_port`)
  - 404/500/413 error handlers

### 2.5: Deduplicate test names
- **Files**: `tests/test_admin.py`, `tests/test_coverage.py`
- **Problem**: `test_bulk_publish` and `test_bulk_delete` appear in both files with slightly different implementations.
- **Fix**: Rename duplicates in `test_coverage.py` to be more specific (e.g., `test_bulk_publish_with_stats`, `test_bulk_delete_with_image_cleanup`).

### 2.6: Deduplicate test fixtures
- **Files**: `test_admin.py`, `test_public.py`, `test_newsletter.py`, `test_coverage.py`
- **Problem**: `sample_post` fixture defined in `conftest.py` but several files create identical posts inline.
- **Fix**: Use shared fixtures where possible. Low priority cleanup.

---

## Wave 3: Code Quality & Configuration

### 3.1: Add `.DS_Store` to `.gitignore`
- **File**: `.gitignore`
- **Status**: Already present in `.gitignore` (line 12). Verify no tracked `.DS_Store` files remain with `git ls-files | grep .DS_Store`. Remove any with `git rm --cached`.

### 3.2: Add `__all__` exports to modules
- **Files**: `app/cache.py`, `app/search.py`, `app/scheduler.py`
- **Fix**:
  - `cache.py`: `__all__ = ["_get_tag_counts", "invalidate_tag_cache"]`
  - `search.py`: `__all__ = ["init_fts", "rebuild_fts", "sync_fts", "remove_fts"]`
  - `scheduler.py`: `__all__ = ["init_scheduler", "get_scheduler_status"]`

### 3.3: Fix import ordering in `admin.py`
- **File**: `app/routes/admin.py:1-27`
- **Problem**: `datetime` import (line 15) appears after third-party imports (lines 9-13).
- **Fix**: Reorder to standard convention: stdlib → third-party → local.

### 3.4: Add upper version bounds to `requirements.txt`
- **File**: `requirements.txt`
- **Fix**: Add upper bounds for major versions:
  ```
  flask>=3.1.0,<4.0
  flask-sqlalchemy>=3.1.1,<4.0
  flask-login>=0.6.3,<1.0
  flask-migrate>=4.1.0,<5.0
  asgiref>=3.8,<4.0
  markdown>=3.7,<4.0
  apscheduler>=3.10.4,<4.0
  werkzeug>=3.1.3,<4.0
  nh3>=0.2.0,<1.0
  ```

### 3.5: Validate `base_url` format in config
- **File**: `app/config.py:77-112`
- **Problem**: `_validate_config()` does not validate `base_url`. Malformed URL breaks RSS, sitemap, email links, and OG images.
- **Fix**: Add validation: check starts with `http://` or `https://`. Warn if contains `localhost`.

### 3.6: Validate pagination config values
- **File**: `app/config.py`
- **Problem**: `dashboard_per_page`, `subscribers_per_page`, `media_per_page`, and `media_max_files` are not validated. Zero or negative values could cause issues.
- **Fix**: Add validation (must be positive integers).

### 3.7: Add docstrings to route handlers
- **Files**: `app/routes/admin.py`, `app/routes/public.py`
- **Problem**: Most route handlers lack docstrings.
- **Fix**: Add single-line docstrings to all route handler functions. Low priority.

### 3.8: Make `ProxyFix` configurable
- **File**: `app/__init__.py:64`
- **Problem**: `ProxyFix` hardcodes proxy count to 1. Behind multiple proxies, may read wrong headers.
- **Fix**: Read proxy count from environment variable or config, defaulting to 1.

---

## Wave 4: Performance

### 4.1: Add eager loading to dashboard post queries
- **File**: `app/routes/admin.py:134-218`
- **Problem**: Dashboard renders posts with their tags, but `Post.tags` relationship is lazy-loaded (N+1 problem).
- **Fix**: Add `.options(joinedload(Post.tags))` to the dashboard query.

---

## Wave 5: Trivial CSS/JS Cleanup

### 5.1: Remove duplicate `bottom`/`right` CSS properties in mobile back-to-top
- **File**: `app/static/css/style.css:2085-2090`
- **Problem**: First `bottom: 20px` and `right: 20px` are immediately overridden by `max()` variants.
- **Fix**: Remove lines 2086-2087, keep only the `max()` versions.

### 5.2: Remove dead `.home-layout` class from templates
- **Files**: `app/templates/index.html:6`, `app/templates/search.html:6`
- **Problem**: `<div class="home-layout">` wrapper has no CSS rule. Does nothing.
- **Fix**: Remove the wrapper `<div>` and closing `</div>` from both templates.

### 5.3: Add `.text-muted` utility class, replace inline styles
- **Files**: `app/static/css/style.css`, `app/templates/admin/users.html:50`, `app/templates/admin/backup.html:9`
- **Problem**: Both templates use `style="color:var(--text-muted)"` inline.
- **Fix**: Add `.text-muted { color: var(--text-muted); }` to CSS. Replace inline styles with `class="text-muted"`.

### 5.4: Fix misleading variable name in theme toggle
- **File**: `app/static/js/main.js:389`
- **Problem**: Variable named `li` but creates a `<span>` element.
- **Fix**: Rename `li` to `wrapper`.

---

## Wave 6: Visual Consistency

### 6.1: Add hero section to tag page
- **File**: `app/templates/tag.html`
- **Problem**: Unlike `index.html` and `search.html`, `tag.html` puts the tag header inside `posts-list` instead of a `hero` section.
- **Fix**: Restructure to match index/search pattern with a `hero` section. Add `.tag-hero` CSS rule with reduced padding. Remove existing `.tag-page-header` block.

### 6.2: Standardize media gallery pagination
- **File**: `app/templates/admin/media.html:36-44`
- **Problem**: Uses `<div class="pagination">` with button-styled links instead of `<nav class="pagination">` with `.page-link` styled links.
- **Fix**: Replace with standard `<nav>` and `<a class="page-link">` elements. Use "Previous" / "Next" text.

### 6.3: Widen tag rename input
- **File**: `app/templates/admin/tags.html:29`
- **Problem**: Uses `class="search-input"` capped at 150px width.
- **Fix**: Add `.tag-rename-input` class with `flex: 1`. Replace `search-input` class.

### 6.4: Remove redundant quick-action buttons from dashboard
- **File**: `app/templates/admin/dashboard.html:52-61`
- **Problem**: Admin navbar already has links to all these sections. Buttons duplicate navigation.
- **Fix**: Remove the entire `<div class="dashboard-section-header">` block.

### 6.5: Add loading indicator for live markdown preview
- **File**: `app/static/js/main.js:257-280`
- **Problem**: During debounce + fetch round-trip, preview shows stale content with no feedback.
- **Fix**: Add subtle "Rendering..." indicator while fetching. Add `.preview-loading` CSS with opacity reduction or spinner. Show "Preview unavailable" on error.

---

## Wave 7: Accessibility & UX

### 7.1: Add system theme change listener
- **File**: `app/static/js/main.js:364-366`
- **Problem**: Initial theme respects `prefers-color-scheme`, but no listener for OS-level theme changes.
- **Fix**: Add `matchMedia` listener that updates theme when OS changes, only when user hasn't explicitly set a preference.

### 7.2: Close mobile menu on outside click and Escape key
- **File**: `app/static/js/main.js:179-186`
- **Problem**: Mobile menu only toggles via hamburger button.
- **Fix**: Add `document.addEventListener('click', ...)` to close when clicking outside. Add `document.addEventListener('keydown', ...)` for Escape key. Update `aria-expanded` attribute.

### 7.3: Add `tabindex="-1"` to skip link target
- **Files**: `app/templates/base.html:65`, `app/templates/admin/base.html:47`
- **Problem**: Skip link points to `#main-content` but without `tabindex="-1"`, some browsers won't focus the target.
- **Fix**: Add `tabindex="-1"` to both `<main id="main-content">` elements.

### 7.4: Add pagination to users page
- **File**: `app/templates/admin/users.html`
- **Problem**: Users list has no pagination.
- **Fix**: Update `users_list()` route to use `db.paginate()` with `per_page=20`. Add standard pagination nav to template. Reuse `dashboard_per_page` config value.

### 7.5: Improve email templates for light-mode email clients
- **Files**: `app/templates/email/confirm.html`, `app/templates/email/newsletter.html`
- **Problem**: Both use hardcoded dark colors (`#0d1117`, `#161b22`, `#e6edf3`). Email clients don't respect CSS custom properties.
- **Fix**: Use neutral/light-friendly colors: background `#f6f8fa`, card `#ffffff`, text `#24292f`, links `#0969da`.

### 7.6: Add `<noscript>` warning for JS-dependent features
- **File**: `app/templates/base.html:21-28`
- **Problem**: Only `<noscript>` block handles mobile menu. No warning for features requiring JavaScript.
- **Fix**: Add subtle banner warning about disabled features (theme toggle, draft autosave, live preview). Add `.noscript-warning` CSS rule.

### 7.7: Hide search button text on mobile
- **Files**: `app/templates/base.html:42`, `app/static/css/style.css`
- **Problem**: On mobile, search form goes to 100% width but "Search" button text still shows.
- **Fix**: Add CSS to hide button text on mobile and show a right arrow icon instead.

---

## Wave 8: Visual Enhancements (CSS/JS Polish)

### 8.1: Improve hero section gradient
- **File**: `app/static/css/style.css`
- **Fix**: Update `.hero-title` gradient to use `var(--accent)` → `var(--accent-hover)` instead of `var(--text)` → `var(--accent)`.

### 8.2: Enhance tag styling
- **File**: `app/static/css/style.css`
- **Fix**: Add pill-shaped tag styling with hover effects, `--accent-dim` background, rounded corners, and subtle lift on hover.

### 8.3: Improve share bar container
- **File**: `app/static/css/style.css`
- **Fix**: Add `.share-bar` container with background, border, and rounded corners. Style individual share buttons with brand hover colors.

### 8.4: Enhance author card
- **File**: `app/static/css/style.css`
- **Fix**: Add `.author-card` styling with avatar border, spacing, and typography hierarchy.

### 8.5: Improve mobile menu animation
- **Files**: `app/static/js/main.js`, `app/static/css/style.css`
- **Fix**: Add slide-in animation with backdrop blur for mobile menu. Add `@keyframes slideInRight` and `fadeIn`.

### 8.6: Increase touch targets
- **File**: `app/static/css/style.css`
- **Fix**: Add `@media (max-width: 768px)` rule with `min-height: 44px` for nav links, buttons, tags, page links, and search inputs.

### 8.7: Mobile editor tab switch
- **Files**: `app/static/css/style.css`, `app/templates/admin/editor.html`
- **Fix**: Add CSS for mobile editor layout. Add tab buttons for mobile toggle (hidden on desktop).

### 8.8: Responsive card improvements
- **File**: `app/static/css/style.css`
- **Fix**: Add mobile-specific card styling: single-column layout, sidebar order change, card image height adjustment.

### 8.9: Enhanced button states
- **File**: `app/static/css/style.css`
- **Fix**: Add `:focus-visible` outline, `:active` scale transform, and `.btn-ghost` variant.

### 8.10: Form validation feedback
- **File**: `app/static/css/style.css`
- **Fix**: Add `.form-group.error` and `.form-error` styling with red border, shadow, and error icon.

### 8.11: Loading states
- **File**: `app/static/css/style.css`
- **Fix**: Add `.btn-loading` with spinner and `.loading-skeleton` with shimmer animation.

### 8.12: Improved empty states
- **File**: `app/static/css/style.css`
- **Fix**: Add `.empty-state` styling with icon, heading, and description.

### 8.13: Refine typography scale
- **File**: `app/static/css/style.css`
- **Fix**: Update `.prose` heading sizes and line heights. Add mobile-specific adjustments.

### 8.14: Improve code block styling
- **File**: `app/static/css/style.css`
- **Fix**: Add `.copy-code-btn` styling with hover reveal effect.

### 8.15: Enhanced stat cards
- **File**: `app/static/css/style.css`
- **Fix**: Add hover effects, typography hierarchy, and trend indicators for dashboard stat cards.

### 8.16: Post list status badges
- **File**: `app/static/css/style.css`
- **Fix**: Add `.status-badge` styling for published/draft states with color-coded backgrounds.

### 8.17: Compact filter bar
- **File**: `app/static/css/style.css`
- **Fix**: Add `.filter-bar` and `.filter-select` styling for dashboard search/filter controls.

### 8.18: Theme toggle animation
- **File**: `app/static/js/main.js`
- **Fix**: Add rotation transform during icon swap in `setThemeIcon()`.

### 8.19: Card hover enhancements
- **File**: `app/static/css/style.css`
- **Fix**: Add `translateY(-4px)` and box-shadow on `.post-card:hover` with cubic-bezier easing.

### 8.20: Flash message progress
- **File**: `app/static/css/style.css`
- **Fix**: Add `::after` pseudo-element with animated progress bar to `.flash` messages.

### 8.21: Focus ring improvements
- **File**: `app/static/css/style.css`
- **Fix**: Add global `:focus-visible` styles and enhanced skip link styling.

### 8.22: Image placeholders and progressive loading
- **Files**: `app/static/css/style.css`, `app/static/js/main.js`
- **Fix**: Add `.img-loading` / `.img-loaded` classes with opacity transitions. Add JS handler for lazy images.

### 8.23: Stagger animation delays and reduced motion
- **File**: `app/static/css/style.css`
- **Fix**: Add `.animate-in` class with `fadeInUp` keyframes. Add `@media (prefers-reduced-motion: reduce)` to disable animations.

---

## Deferred / Monitoring

### D.1: Page View Optimization
Every unique post visit triggers an individual `db.session.commit()`. SQLite handles small transactions well for a personal blog. Consider batching via `after_request` handler if traffic grows significantly.

### D.2: `admin.py` Modularization
At 987 lines, `admin.py` is large but well-organized. Splitting into sub-modules would add complexity without clear benefit for a single-developer project. Revisit if the file exceeds 1500 lines.

### D.3: Dashboard Query Caching
7+ queries per dashboard load with no caching. Low priority for a personal blog.

### D.4: PageView Archival
No cleanup mechanism for `PageView` table. Table grows unbounded. Low priority.

### D.5: Media Gallery Optimization
Sorts entire directory on each page load. Bounded at 1000 files, acceptable for now.

---

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Run after each wave to verify no regressions. All 186 tests must continue to pass.

## Execution Order & Parallelization

Waves are ordered by dependency and risk. Within each wave, items can be parallelized using sub-agents where they don't touch the same files:

| Wave | Description | Parallelizable | Notes |
|------|-------------|----------------|-------|
| 1 | Bug Fixes | Partially | 1.1 (`__init__.py`) and 1.2 (`search.py`) are independent. 1.3-1.5 all touch different files. |
| 2 | Test Migration & Coverage | Yes | Each test file can be handled by a separate sub-agent. |
| 3 | Code Quality & Config | Partially | 3.1-3.8 touch different files and can be parallelized. |
| 4 | Performance | No | Single item. |
| 5 | Trivial CSS/JS | Yes | 5.1-5.4 touch different files. |
| 6 | Visual Consistency | Partially | 6.1-6.5 touch different template/CSS/JS files. |
| 7 | Accessibility & UX | Partially | 7.1-7.2 both touch `main.js` (sequential). 7.3-7.7 touch different files (parallel). |
| 8 | Visual Enhancements | Partially | All CSS items (8.1-8.23) touch `style.css` — best done by a single agent to avoid conflicts. JS items (8.5, 8.7, 8.18, 8.22) can be done separately. |

## Risk Assessment

| Wave | Risk | Rollback |
|------|------|----------|
| 1 — Bug Fixes | Low-Medium | Easy |
| 2 — Tests | None | Trivial |
| 3 — Code Quality | Low | Easy |
| 4 — Performance | Low | Easy |
| 5 — Trivial CSS/JS | None | Trivial |
| 6 — Visual Consistency | Low | Easy |
| 7 — Accessibility & UX | Low-Medium | Easy |
| 8 — Visual Enhancements | Low | Easy (CSS/JS only) |
