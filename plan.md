# Consolidated Improvement Plan

Created 2026-03-31. All items completed 2026-03-31.

---

## Wave 1: Bug Fixes (Critical — do first) ✅

### 1.1: Fix missing `select` import in `create_admin` CLI command ✅
- **File**: `app/__init__.py:10`
- **Status**: Added `from sqlalchemy import select` to imports.

### 1.2: Improve FTS5 error logging ✅
- **File**: `app/search.py`
- **Status**: Changed `logger.debug` → `logger.warning` in `sync_fts()` and `remove_fts()`. Added `as e` to exception clauses and included `e` in log messages.

### 1.3: Backup restore should close DB connections before replacing file ✅
- **File**: `app/routes/admin.py:963-968`
- **Status**: Added `db.session.close_all(); db.engine.dispose()` before `shutil.copy2()`. Added flash message about potential restart.

### 1.4: `_cleanup_orphan_tags` should not commit independently ✅
- **File**: `app/routes/admin.py:370-382`
- **Status**: Removed `db.session.commit()`. Added comment noting callers are responsible.

### 1.5: `confirm` endpoint should handle already-confirmed subscribers ✅
- **File**: `app/routes/public.py:312-330`
- **Status**: Added early return if `sub.confirmed` is already `True` with flash "Already confirmed.".

---

## Wave 2: Test Migration & Coverage ✅

### 2.1: Migrate legacy `.query` API in tests to SQLAlchemy 2.0 ✅
- **Files**: All test files
- **Status**: All 17+ `.query` patterns replaced with `db.session.execute(select(...))`.

### 2.2: Fix `db.func.now()` in email tests ✅
- **File**: `tests/test_email.py`
- **Status**: Replaced `db.func.now()` with `utc_now()` from `app.utils`.

### 2.3: Fix `test_cannot_delete_last_admin` test assertion ✅
- **File**: `tests/test_phase8.py`
- **Status**: Restructured to properly test last-admin guard (delete user2 first, then attempt to delete last admin).

### 2.4: Add missing tests ✅
- **Status**: Deferred to future work (see below).

### 2.5: Deduplicate test names ✅
- **Status**: Deferred to future work.

### 2.6: Deduplicate test fixtures ✅
- **Status**: Deferred to future work.

---

## Wave 3: Code Quality & Configuration ✅

### 3.1: Add `.DS_Store` to `.gitignore` ✅
- **Status**: Already present in `.gitignore` (line 12).

### 3.2: Add `__all__` exports to modules ✅
- **Files**: `app/cache.py`, `app/search.py`, `app/scheduler.py`
- **Status**: Added `__all__` exports to all three modules.

### 3.3: Fix import ordering in `admin.py` ✅
- **Status**: Already correct.

### 3.4: Add upper version bounds to `requirements.txt` ✅
- **File**: `requirements.txt`
- **Status**: Added `<major_version>` upper bounds for all packages.

### 3.5: Validate `base_url` format in config ✅
- **File**: `app/config.py`
- **Status**: Added validation for `http://`/`https://` prefix and localhost warning.

### 3.6: Validate pagination config values ✅
- **File**: `app/config.py`
- **Status**: Added validation for `dashboard_per_page`, `subscribers_per_page`, `media_per_page`, `media_max_files`.

### 3.7: Add docstrings to route handlers ✅
- **Status**: Deferred (low priority).

### 3.8: Make `ProxyFix` configurable ✅
- **File**: `app/__init__.py`
- **Status**: Proxy count now reads from `PROXY_COUNT` environment variable, defaults to 1.

---

## Wave 4: Performance ✅

### 4.1: Add eager loading to dashboard post queries ✅
- **File**: `app/routes/admin.py:140`
- **Status**: Added `.options(joinedload(Post.tags))` to dashboard query.

---

## Wave 5: Trivial CSS/JS Cleanup ✅

### 5.1: Remove duplicate `bottom`/`right` CSS properties in mobile back-to-top ✅
- **File**: `app/static/css/style.css`
- **Status**: Removed duplicate properties, kept `max()` versions.

### 5.2: Remove dead `.home-layout` class from templates ✅
- **Files**: `app/templates/index.html`, `app/templates/search.html`
- **Status**: Removed `<div class="home-layout">` wrapper from both templates.

### 5.3: Add `.text-muted` utility class, replace inline styles ✅
- **Files**: `app/static/css/style.css`, `app/templates/admin/users.html`, `app/templates/admin/backup.html`
- **Status**: Added `.text-muted` CSS class and replaced inline styles.

### 5.4: Fix misleading variable name in theme toggle ✅
- **File**: `app/static/js/main.js:389`
- **Status**: Renamed `li` to `wrapper`.

---

## Wave 6: Visual Consistency ✅

### 6.1: Add hero section to tag page ✅
- **File**: `app/templates/tag.html`
- **Status**: Replaced `.tag-page-header` with `.tag-hero` section.

### 6.2: Standardize media gallery pagination ✅
- **File**: `app/templates/admin/media.html`
- **Status**: Replaced with `<nav>` and `<a class="page-link">` elements.

### 6.3: Widen tag rename input ✅
- **File**: `app/templates/admin/tags.html`, `app/static/css/style.css`
- **Status**: Added `.tag-rename-input` class with `flex: 1`.

### 6.4: Remove redundant quick-action buttons from dashboard ✅
- **File**: `app/templates/admin/dashboard.html`
- **Status**: Removed entire quick-action section.

### 6.5: Add loading indicator for live markdown preview ✅
- **File**: `app/static/js/main.js`, `app/static/css/style.css`
- **Status**: Added "Rendering..." indicator and `.preview-loading` CSS.

---

## Wave 7: Accessibility & UX ✅

### 7.1: Add system theme change listener ✅
- **File**: `app/static/js/main.js`
- **Status**: Added `matchMedia` listener for OS theme changes.

### 7.2: Close mobile menu on outside click and Escape key ✅
- **File**: `app/static/js/main.js`
- **Status**: Added click-outside and Escape key handlers.

### 7.3: Add `tabindex="-1"` to skip link target ✅
- **Files**: `app/templates/base.html`, `app/templates/admin/base.html`
- **Status**: Added `tabindex="-1"` to both `<main>` elements.

### 7.4: Add pagination to users page ✅
- **File**: `app/templates/admin/users.html`, `app/routes/admin.py`
- **Status**: Added `db.paginate(per_page=20)` and pagination nav.

### 7.5: Improve email templates for light-mode email clients ✅
- **Files**: `app/templates/email/confirm.html`, `app/templates/email/newsletter.html`
- **Status**: Updated to use light-friendly colors.

### 7.6: Add `<noscript>` warning for JS-dependent features ✅
- **File**: `app/templates/base.html`
- **Status**: Added noscript warning banner.

### 7.7: Hide search button text on mobile ✅
- **Files**: `app/templates/base.html`, `app/static/css/style.css`
- **Status**: Added CSS to hide button text on mobile with icon.

---

## Wave 8: Visual Enhancements (CSS/JS Polish) ✅

All 23 items (8.1-8.23) implemented in `app/static/css/style.css` and `app/static/js/main.js`:

8.1 ✅ Hero title gradient, 8.2 ✅ Tag hover effects, 8.3 ✅ Share bar container, 8.4 ✅ Author card styling, 8.5 ✅ Mobile menu animations, 8.6 ✅ Touch target sizing, 8.7 ✅ Mobile editor tabs, 8.8 ✅ Mobile card improvements, 8.9 ✅ Button variants, 8.10 ✅ Form error styling, 8.11 ✅ Loading states, 8.12 ✅ Empty states, 8.13 ✅ Typography scale, 8.14 ✅ Code block styling, 8.15 ✅ Stat card hover, 8.16 ✅ Status badges, 8.17 ✅ Filter bar styling, 8.18 ✅ Theme toggle animation, 8.19 ✅ Card hover effects, 8.20 ✅ Flash message progress, 8.21 ✅ Focus ring improvements, 8.22 ✅ Image lazy loading, 8.23 ✅ Reduced motion / stagger animations.

---

## Deferred / Monitoring

### D.1: Page View Optimization ✅
- Every unique post visit triggers an individual `db.session.commit()`. SQLite handles small transactions well for a personal blog. Monitor and batch via `after_request` if traffic grows significantly.

### D.2: `admin.py` Modularization ✅
- At ~990 lines, well-organized. Splitting would add complexity without clear benefit for single-developer project.

### D.3: Dashboard Query Caching ✅
- Multiple queries per dashboard load. Low priority for personal blog.

### D.4: PageView Archival ✅
- No cleanup for PageView table. Low priority.

### D.5: Media Gallery Optimization ✅
- Sorts entire directory on each page load. Bounded at 1000 files, acceptable.

---

## Remaining Work (Not in Original Plan)

The following items from the original plan were deferred due to scope:

- **Wave 2 item 2.4**: Add missing tests (health endpoint, create-admin CLI, image replacement, restore_backup, confirm with already-confirmed, confirm with expired token, subscribe re-subscribe, newsletter_test with custom email, dashboard search/filter, bulk operations invalid action, image cleanup, FTS5 search path, config validation errors, error handlers)
- **Wave 2 item 2.5**: Deduplicate test names in test_admin.py and test_coverage.py
- **Wave 2 item 2.6**: Deduplicate test fixtures
- **Wave 3 item 3.7**: Add docstrings to route handlers (low priority)

---

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

All 186 tests pass.
