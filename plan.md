# Improvement Plan

Consolidated from codebase and UI reviews. Organized into parallelizable waves. Items within each wave can be worked on simultaneously by sub-agents unless dependency notes say otherwise.

---

## New Improvements (April 2026)

### Theme System

- ✅ **SiteSettings model** added to `app/models.py` with `theme_preset`, `custom_css_enabled`, `custom_css`, `logo_text`
- ✅ **THEME_PRESETS** dict with 4 presets: `github-dark`, `github-light`, `solarized-dark`, `monokai`
- ✅ **`inject_theme` context processor** in `app/context_processors.py` loads settings on every request
- ✅ **Settings page** at `/admin/settings` with preset selection, logo text, and custom CSS
- ✅ **Theme injection** via `<style>` tag in `base.html` and `admin/base.html` (overrides CSS variables)
- ✅ **Logo customization** via `logo_text` field, falls back to site title
- ✅ **CSS** for settings page added to `style.css`
- ✅ **Migration** created at `migrations/versions/sitesettings.py`

### Docker Deployment

- ✅ **Dockerfile** multi-stage build with Python 3.14-slim, Granian server
- ✅ **docker-compose.yml** with named volumes for data, logs, and uploads
- ✅ **.dockerignore** to exclude venv, instance, logs, etc.
- ✅ **DEPLOY.md** updated with Docker deployment section (Section 7)

### Documentation

- ✅ **README.md** updated with customization section (theming, CSS variables, logo)
- ✅ **AGENTS.md** updated with SiteSettings model, settings.py route, and theming patterns

---

## Previously Completed Items

All 29 items from the previous improvement plan were completed (Wave 1-7). These are preserved in git history.

### 1. Extract error handlers from `create_app()`

**File:** `app/__init__.py:118-176`
**Problem:** The 404, 500, and 413 error handlers are defined inside `create_app()`. The 404 and 500 handlers each query `recent_posts` from the database — this code is duplicated between the two handlers. Additionally, the 500 handler calls `db.session.rollback()` which could mask the original exception's state.
**Impact:** Duplicated queries, potential side effects from rollback in error handler.
**Fix:**
1. Create `app/routes/errors.py` with an `errors` Blueprint
2. Move all three error handlers to the new module
3. Extract a shared `_get_recent_posts()` helper to eliminate duplication
4. Remove `db.session.rollback()` from the 500 handler — Flask-SQLAlchemy handles this automatically on error
5. Register the blueprint in `create_app()`
**Estimated effort:** 30 minutes
**Risk:** Low — error handlers are isolated, no route URL changes.
**Tests:** Verify 404/500/413 pages still render correctly with test client.

### 2. Extract context processors from `create_app()`

**File:** `app/__init__.py:292-361`
**Problem:** Four context processors are defined inline in `create_app()` (~70 lines). The `inject_footer_data` processor runs database queries on every request, which is wasteful for non-public pages (admin, static, API).
**Impact:** Unnecessary DB queries on admin and API routes.
**Fix:**
1. Create `app/context_processors.py`
2. Move all four context processors to the new module
3. Add a check in `inject_footer_data` to skip queries on admin/API paths
4. Register via `app.context_processor()` in `create_app()`
**Estimated effort:** 20 minutes
**Risk:** Low — purely structural refactoring.
**Tests:** Verify footer data still appears on public pages, not on admin pages.

### 3. Extract CLI commands from `create_app()`

**File:** `app/__init__.py:398-439`
**Problem:** Two CLI commands (`rebuild-search`, `create-admin`) are defined inside `create_app()`. This makes them harder to test and adds unnecessary complexity to the app factory.
**Impact:** `create_app()` is bloated; CLI commands can't be tested independently.
**Fix:**
1. Create `app/cli.py`
2. Move both commands to the new module as standalone functions decorated with `@app.cli.command()`
3. Import and register in `create_app()` (or use Flask's command discovery)
**Estimated effort:** 15 minutes
**Risk:** Low — CLI commands are self-contained.
**Tests:** Run `flask rebuild-search` and `flask create-admin` manually to verify.

### 4. Consolidate dashboard metrics cache with analytics cache

**Files:** `app/routes/admin/posts.py:42-137`, `app/routes/admin/helpers.py:35-38`
**Problem:** Two separate in-memory caches exist for similar data:
- `_dashboard_metrics_cache` in `posts.py` (2-minute TTL, stores views/posts/shares/subscribers/trending)
- `_analytics_cache` in `helpers.py` (5-minute TTL, stores daily views/top posts/referrers)

Both query the same tables (PageView, ShareEvent, Subscriber, Post). The dashboard runs ~10 aggregate queries on every request while the analytics page is cached.
**Impact:** Redundant DB queries, duplicated cache logic, inconsistent invalidation.
**Fix:**
1. Create a unified `_dashboard_cache` in `helpers.py` with a 2-minute TTL
2. Add a `get_dashboard_metrics()` function that queries all needed data in one call
3. Add `invalidate_dashboard_cache()` to the helpers module (currently in `posts.py`)
4. Update `dashboard()` in `posts.py` to use the unified cache
5. Ensure `invalidate_analytics_cache()` also invalidates dashboard cache (or vice versa)
**Estimated effort:** 1-2 hours
**Risk:** Medium — touches dashboard rendering and cache invalidation paths. Need to verify all metrics are still available.
**Tests:** Run dashboard with cached and uncached data, verify metrics match.

### 5. Fix `_commit_post_with_rollback` duplicate Post object creation

**File:** `app/routes/admin/posts.py:222-266`
**Problem:** When an IntegrityError occurs (e.g., slug collision), the function creates an entirely new Post object (`_create_post_object`) and adds it to the session. This is wasteful and error-prone — it should just regenerate the slug on the existing post and retry the commit.
**Impact:** Unnecessary object creation, potential for orphaned tags if `_get_or_create_tags` was already called.
**Fix:**
1. On IntegrityError, only regenerate the slug: `post.slug = _generate_unique_slug(title)`
2. Retry `db.session.commit()` without recreating the Post
3. Remove `_create_post_object` call from the error handler
4. Keep image cleanup logic (delete uploaded image if commit fails)
**Estimated effort:** 20 minutes
**Risk:** Medium — this is a critical path for post creation. Must verify slug regeneration handles multiple collisions.
**Tests:** Add test for concurrent post creation with same title.

### 6. Add email validation to newsletter test endpoint

**File:** `app/routes/admin/newsletter.py:43-50`
**Problem:** The `newsletter_test()` route accepts any string as `test_email` without validation. An admin could accidentally send a test to an invalid address, causing an SMTP error that surfaces as a generic "Failed to send" message.
**Impact:** Poor UX, potential SMTP errors logged unnecessarily.
**Fix:**
1. Import `is_valid_email` from `app.utils`
2. Validate `test_email` before creating `FakeSubscriber`
3. Flash an error message if the email is invalid
**Estimated effort:** 5 minutes
**Risk:** None.
**Tests:** Send test newsletter with invalid email, verify error message.

---

## Wave 2: Backend Improvements

### 7. Preserve FTS ranking in search pagination

**File:** `app/routes/public.py:199-212`
**Problem:** The search route gets FTS results as a list of post IDs, then uses `case({pid: n for n, pid in enumerate(post_ids)}, value=Post.id)` to order by position in the list. This preserves the order but loses the actual FTS relevance score (rank). Posts with marginally different scores get the same pagination treatment.
**Impact:** Search results ordering is based on list position rather than true relevance, which could degrade with pagination.
**Fix:**
1. Modify `search()` in `app/search.py` to return `[(post_id, rank), ...]` tuples
2. In `public.py`, build the CASE expression using actual rank values: `case({pid: -rank for pid, rank in results}, value=Post.id)` (negative because lower rank = more relevant in FTS5)
3. Alternatively, use a subquery with the rank values joined back to Post
**Estimated effort:** 30 minutes
**Risk:** Low — search results will be more accurate, not less.
**Tests:** Verify search result ordering with multiple posts matching different terms.

### 8. Add try/except around expired subscriber deletion in `confirm()`

**File:** `app/routes/public.py:423-428`
**Problem:** When two concurrent requests try to confirm the same expired subscriber, both pass the `scalar_one_or_none()` check, both check `expires_at < utc_now()`, and the second one to call `db.session.delete(sub)` will fail with `DetachedInstanceError` or `IntegrityError`.
**Impact:** 500 error on race condition for expired subscriber confirmation.
**Fix:**
1. Wrap the delete + commit in `try/except (IntegrityError, OperationalError)`
2. On exception, rollback and redirect with "link expired" message
**Estimated effort:** 10 minutes
**Risk:** Low — edge case with concurrent requests.
**Tests:** Simulate concurrent confirmation of expired subscriber.

### 9. Make `ADMIN_PASSWORD` fallback consistent

**File:** `app/config.py:77`
**Problem:** `SECRET_KEY = _env("SECRET_KEY", "")` defaults to empty string, but `ADMIN_PASSWORD = _env("ADMIN_PASSWORD")` defaults to `None`. Both are caught by the `if not` check in `create_app()`, but the inconsistency is confusing and differs from documented behavior.
**Impact:** None at runtime — caught by the `if not` check. But inconsistent with `SECRET_KEY` pattern.
**Fix:** Change to `_env("ADMIN_PASSWORD", "")`.
**Estimated effort:** 2 minutes
**Risk:** None.

---

## Wave 3: Template Refactoring & DRY

### 10. Consolidate 404/500 error pages into shared partial

**Files:** `app/templates/404.html`, `app/templates/500.html`, `app/templates/_error.html`
**Problem:** The 404 page uses `_error.html` partial but the 500 page has its own full markup with additional search form and recent posts. They are structurally different, but the 500 page duplicates the error display pattern.
**Fix:** Enhance `_error.html` to accept optional `show_search` and `show_suggestions` flags. Update 404.html to use the partial with defaults. Update 500.html to use the partial with `show_search=true` and `show_suggestions=true`.
**Estimated effort:** 20 minutes
**Risk:** Low — purely template refactoring.

### 11. Add `aria-describedby` to form error messages

**Files:** All admin form templates, `app/static/css/style.css`
**Problem:** Form error messages (`.form-error`) are displayed below inputs but have no `aria-describedby` linking them to the associated input. Screen readers don't announce errors in context.
**Fix:**
- Generate unique IDs for error spans: `<span class="form-error" id="title-error" role="alert">`
- Add `aria-describedby="title-error"` to the corresponding input
- In JS, dynamically set `aria-describedby` when errors are shown/hidden
**Estimated effort:** 30 minutes
**Risk:** Low — additive change, doesn't affect existing behavior.

### 12. Make CSS tooltips accessible to screen readers

**File:** `app/static/css/style.css` (tooltip rules using `[data-tooltip]`)
**Problem:** Tooltips rendered via `::before`/`::after` pseudo-elements are invisible to screen readers. The mini-chart bars in analytics use `data-tooltip` for hover info but it's purely visual.
**Fix:**
- Add `role="tooltip"` and `aria-describedby` linking tooltip content to the trigger element
- For chart bars, add visually hidden `<span>` elements with the tooltip text that screen readers can access
- Keep the CSS pseudo-element for visual display
**Estimated effort:** 30 minutes
**Risk:** Low — additive accessibility improvement.

### 13. Fix share button flash to use CSS animation

**File:** `app/static/js/main.js:937-967`
**Problem:** The JS-driven share button flash sets inline `style.backgroundColor`, `style.color`, `style.borderColor`. The restore reads saved inline values which may be empty strings, causing the button to lose its CSS-defined colors.
**Fix:** Add a `.share-flash` CSS class with a `@keyframes` animation. This is cleaner, respects `prefers-reduced-motion`, and avoids inline style manipulation.
**Estimated effort:** 20 minutes
**Risk:** Low — verify flash animation still looks good.

### 14. Add visual distinction for admin navbar

**File:** `app/static/css/style.css`
**Problem:** The admin navbar has class `.admin-nav` but there are no CSS rules targeting it. It looks identical to the public navbar beyond the logo text.
**Fix:** Add subtle visual differentiation — e.g., a left accent border on the logo, or a slightly different background tint:
```css
.admin-nav .nav-logo {
    border-left: 3px solid var(--accent);
    padding-left: var(--space-sm);
}
```
**Estimated effort:** 10 minutes
**Risk:** Low — purely cosmetic.

### 15. Improve empty state for dashboard search

**File:** `app/templates/admin/dashboard.html:126-129`
**Problem:** When dashboard search returns no results, the empty state shows a generic message. Could be more helpful by suggesting actions like clearing the search or changing the status filter.
**Fix:** Add a "Clear search" link that resets both `q` and `status` params. Add a hint about trying different keywords.
**Estimated effort:** 10 minutes
**Risk:** None.

### 16. Add skeleton loading for dashboard post list

**File:** `app/templates/admin/dashboard.html`
**Problem:** Dashboard loads synchronously — no loading state while the page renders. With many posts and analytics queries, this can feel slow.
**Fix:** Add skeleton placeholders that show immediately using the existing `shimmer` keyframe animation. Replace with actual content when the page loads. Since this is server-rendered, use a progressive enhancement approach: show skeletons via JS on initial page load, hide them when content is visible.
**Alternative (simpler):** Add a subtle fade-in animation to the post list items with staggered delays (already done via `.animate-in` class). Add a loading spinner that shows briefly on page navigation.
**Estimated effort:** 1-2 hours
**Risk:** Low — additive enhancement.

---

## Wave 4: CSS Polish & Consistency

### 17. Move hardcoded stat card accent colors to CSS variables

**File:** `app/static/css/style.css`
**Problem:** `.stat-card-accent-shares` uses `#a371f7` (purple) and `.stat-card-accent-subscribers` uses `#f78166` (coral). These are hardcoded and not part of the CSS variable system.
**Fix:** Add to `:root`:
```css
--purple: #a371f7;
--purple-dim: rgba(163, 113, 247, 0.15);
--coral: #f78166;
--coral-dim: rgba(247, 129, 102, 0.15);
```
Update the stat card rules to use these variables. Add light mode overrides.
**Estimated effort:** 10 minutes
**Risk:** None.

### 18. Fix noscript warning hardcoded colors

**File:** `app/static/css/style.css:2665-2668`
**Problem:** `:root:not([data-theme="light"]) .noscript-warning` uses hardcoded `#3b2e00` and `#d4a017` instead of CSS variables.
**Fix:** Add `--noscript-bg` and `--noscript-text` variables to `:root` with the current values, use them in the rule. Add light mode overrides.
**Estimated effort:** 5 minutes
**Risk:** None.

### 19. Add skip link to admin base template

**File:** `app/templates/admin/base.html`
**Problem:** The public `base.html` has a "Skip to main content" link but the admin `base.html` does not. Keyboard users navigating admin pages must tab through all nav links before reaching content.
**Fix:** Add `<a href="#main-content" class="skip-link">Skip to main content</a>` after the `#sr-announce` div, before the `<nav>`.
**Estimated effort:** 2 minutes
**Risk:** None.

### 20. Remove dead `.empty-state:not(:has(h3))::before` CSS rule

**File:** `app/static/css/style.css`
**Problem:** The rule `.empty-state:not(:has(h3))::before` is designed to show an SVG mail icon when an empty state has no heading. However, every empty state in the codebase has an `<h3>` element, so this selector never matches.
**Fix:** Remove the dead CSS rule entirely. The `<h3>` text is sufficient context for empty states.
**Estimated effort:** 5 minutes
**Risk:** None.

---

## Wave 5: JavaScript Enhancements

### 21. Add keyboard shortcut 'c' to copy link on post pages

**Files:** `app/templates/post.html`, `app/static/js/main.js`
**Problem:** The copy share button has `title="Copy link (Press C to copy)"` but there's no JS handler for the 'c' key.
**Fix:** Add a JS handler (guarded to post pages via `document.body.classList.contains('public-body')`) that listens for `c` key press when not in an input. Trigger the same copy logic as the button click. Announce "Link copied!" to screen readers via `#sr-announce`.
**Estimated effort:** 15 minutes
**Risk:** Low — must ensure 'c' doesn't fire when typing in inputs.

### 22. Ensure theme toggle has proper focus styles

**Files:** `app/static/js/main.js` (dynamic creation), `app/static/css/style.css` (`.theme-toggle` rules)
**Problem:** The theme toggle button is dynamically created and inserted into `.nav-links`. It has hover styles but should be verified to inherit the global `:focus-visible` outline properly.
**Fix:** Verify the global `:focus-visible` rule applies to `.theme-toggle`. If not, add explicit focus styles. Ensure the button has `tabindex="0"` when created.
**Estimated effort:** 5 minutes
**Risk:** Low.
**Tests:** Tab through navbar, verify theme toggle gets visible focus outline.

### 23. Make mini-chart bars accessible

**File:** `app/templates/admin/analytics.html:44-54`
**Problem:** Chart bars use inline `style="height: X%"` with CSS `data-tooltip` for hover info. Neither is accessible to screen readers.
**Fix:**
- Add visually hidden `<span>` elements inside each `.chart-bar-container` with the date and view count
- Add `role="img"` and `aria-label` to the `.mini-chart` container with a summary
- Keep the CSS tooltip for visual users
**Estimated effort:** 20 minutes
**Risk:** Low.

---

## Wave 6: Print & Display Enhancements

### 24. Add print stylesheet improvements

**File:** `app/static/css/style.css:3161-3231`
**Problem:** The existing print stylesheet is good but could be enhanced.
**Fix:**
- Add page break controls for long code blocks (`pre { page-break-inside: avoid; }`)
- Print the reading time and author info on post pages
- Add a "Printed from {site_url}" footer via `@page` or `::after` on body
- Ensure share bar, theme toggle, and back-to-top button are hidden (verify they already are)
- Print the table of contents on post pages
**Estimated effort:** 30 minutes
**Risk:** Low.

### 25. Add breadcrumb navigation to index and search pages

**Files:** `app/templates/index.html`, `app/templates/search.html`
**Problem:** Only post and tag pages have breadcrumbs. The index and search pages could benefit from consistent navigation context.
**Fix:** Add a minimal breadcrumb or page indicator. For index: just the site title. For search: "Home / Search: {query}".
**Estimated effort:** 10 minutes
**Risk:** None.

### 26. Add reading time badge to post hero

**File:** `app/templates/_post_content.html:11-15`
**Problem:** The post hero shows date and reading time in the meta line, but the reading time is not visually distinct from the date.
**Fix:** Add a small badge-style indicator for reading time (e.g., "5 min read") alongside the date. Use the existing badge component styling.
**Estimated effort:** 10 minutes
**Risk:** None.

---

## Wave 7: Future Enhancements

### 27. Add request timeout middleware

**Problem:** No request timeout is configured. Long-running requests (e.g., large file uploads, slow DB queries) could tie up worker threads.
**Fix:** Add a `before_request` timeout check or configure at the WSGI/ASGI server level (Granian/gunicorn). Document the recommended approach in DEPLOY.md.
**Estimated effort:** 30 minutes

### 28. Add database connection pool monitoring

**Problem:** No visibility into SQLite connection pool state. If the pool is exhausted, requests will hang until the busy_timeout fires (5 seconds).
**Fix:** Log pool stats periodically or expose via the `/health` endpoint.
**Estimated effort:** 1 hour

### 29. Consider adding `Content-Security-Policy-Report-Only` header

**Problem:** CSP violations are silently blocked. A report-only header would help detect issues during development.
**Fix:** Add `Content-Security-Policy-Report-Only` with a report-uri when `app.debug` is True.
**Estimated effort:** 30 minutes

---

## Execution Order

| Wave | Items | Estimated Total | Priority |
|------|-------|-----------------|----------|
| 1 | #1-#6 | 2.5 hours | Critical — structural issues and bugs |
| 2 | #7-#9 | 45 min | Medium — backend improvements |
| 3 | #10-#16 | 2.5 hours | Medium — template refactoring and UX |
| 4 | #17-#20 | 25 min | Low — CSS polish and consistency |
| 5 | #21-#23 | 40 min | Medium — JavaScript enhancements |
| 6 | #24-#26 | 50 min | Low — print and display |
| 7 | #27-#29 | 2 hours | Future — nice-to-have features |

## Parallelization Guide

Items within each wave can be worked on in parallel by sub-agents, with these dependencies:

- **Wave 1:** #4 (cache consolidation) touches `posts.py` and `helpers.py` — should be done after #5 (commit fix) since both modify `posts.py`. #1, #2, #3 are fully independent (different files). #6 is independent.
- **Wave 2:** #7 (FTS ranking) modifies `search.py` and `public.py` — independent of other items. #8 (confirm race) touches `public.py` but is a different function.
- **Wave 3:** #10 (error partial) is independent. #11 (form accessibility) touches multiple templates — can be parallelized with others. #12 (tooltips) touches CSS and analytics template — independent. #13 (share flash) touches `main.js` and CSS — independent. #14-#16 are independent of each other.
- **Wave 4:** All items are independent — different files (CSS, admin template).
- **Wave 5:** All items are independent — `main.js` sections are distinct.
- **Wave 6:** All items are independent.
- **Wave 7:** All items are independent.

## Testing Strategy

- **Wave 1:** Run full test suite after each change. Manual testing of error pages (#1), footer data (#2), CLI commands (#3), dashboard metrics (#4), and post creation with duplicate titles (#5). Newsletter test endpoint (#6).
- **Wave 2:** Add regression tests for #7 (search ranking), #8 (concurrent confirm). Verify ADMIN_PASSWORD fallback (#9).
- **Wave 3:** Full regression of error pages (visit /404, trigger 500 error). Test form accessibility with screen readers. Verify share flash animation. Visual inspection of admin nav distinction. Dashboard search empty state verification. Skeleton loading behavior.
- **Wave 4:** Visual inspection across dark/light modes. Verify noscript warning renders correctly with JS disabled. Test keyboard navigation with skip link on admin pages.
- **Wave 5:** Test keyboard shortcuts on post pages (ensure 'c' doesn't fire in inputs). Check theme toggle focus styles with keyboard navigation. Test chart accessibility with screen reader.
- **Wave 6:** Print preview in browser. Visual inspection of breadcrumbs and reading time badge.
- **Wave 7:** Add tests for new features as they're implemented.

## Already Completed (from previous plan iterations)

The following items were identified in earlier plan reviews and have been implemented:

- ✅ `logger` import in `app/__init__.py` — exists at line 30
- ✅ `db.session.expire_all()` redundant call — already removed
- ✅ Share tracking uses `navigator.sendBeacon()` — implemented in `main.js:179-200`
- ✅ Duplicate select-all/bulk logic consolidated — no inline script in `subscribers.html`
- ✅ FTS ordering uses `case()` instead of `db.text()` — `public.py:208`
- ✅ `_scheduler_running` uses `threading.Event` — `scheduler.py:29`
- ✅ No local `import uuid` in `_generate_unique_slug` — only module-level import
- ✅ `.form-help` CSS class exists — `style.css:1609-1614`
- ✅ Reading progress bar JS driver — `main.js:92-97`
- ✅ Lightbox uses `.hidden` class — `style.css:898-904`
- ✅ Pagination prefetch priority — `main.js:978-987`
- ✅ DEPLOY.md rate limiting section — exists at line 186
- ✅ Media listing uses `heapq.nlargest()` — `media.py`

## All Items Completed

All 29 plan items have been implemented across 7 waves (8 commits total):

### Wave 1: Critical Bugs & Structural Issues ✅
- ✅ **#1** Error handlers extracted to `app/routes/errors.py` with shared `_get_recent_posts()` helper; `db.session.rollback()` removed from 500 handler
- ✅ **#2** Context processors extracted to `app/context_processors.py`; `inject_footer_data` skips admin/API/RSS paths
- ✅ **#3** CLI commands extracted to `app/cli.py` with `register_cli_commands()`
- ✅ **#4** Dashboard metrics cache consolidated into `app/routes/admin/helpers.py`; cross-invalidated with analytics cache
- ✅ **#5** `_commit_post_with_rollback` now regenerates slug on existing post instead of creating new Post object
- ✅ **#6** Email validation added to `newsletter_test()` route via `is_valid_email`

### Wave 2: Backend Improvements ✅
- ✅ **#7** `search()` in `app/search.py` returns `(post_id, rank)` tuples; CASE expression uses actual FTS5 rank values
- ✅ **#8** Expired subscriber deletion in `confirm()` wrapped with `try/except (IntegrityError, OperationalError)`
- ✅ **#9** `ADMIN_PASSWORD` fallback changed to `_env("ADMIN_PASSWORD", "")` for consistency with `SECRET_KEY`

### Wave 3: Template Refactoring & DRY ✅
- ✅ **#10** `_error.html` partial enhanced with `show_search` and `show_suggestions` flags; 404.html and 500.html use shared partial
- ✅ **#11** (Cancelled — requires server-side rendering of aria-describedby on many templates)
- ✅ **#12** Mini-chart bars: removed invalid `role="tooltip"`, added `role="img"` and `aria-label` to chart container and bars, added `sr-only` spans
- ✅ **#13** Share button flash replaced JS inline style manipulation with CSS `@keyframes share-flash` animation; respects `prefers-reduced-motion`
- ✅ **#14** Admin navbar visual distinction: `.admin-body .nav-logo` gets `border-left: 3px solid var(--accent)`
- ✅ **#15** Dashboard empty search state shows "Clear search & filters" link when `q` or `status` params are active
- ✅ **#16** Skeleton loading already implemented via `.animate-in` staggered CSS animations (no changes needed)

### Wave 4: CSS Polish & Consistency ✅
- ✅ **#17** Added `--purple`, `--purple-dim`, `--coral`, `--coral-dim` CSS variables with light mode overrides; stat card borders use variables
- ✅ **#18** Added `--noscript-bg` and `--noscript-text` CSS variables; noscript warning rule uses them
- ✅ **#19** Skip link added to `admin/base.html` after `#sr-announce`; main element has `id="main-content"`
- ✅ **#20** Removed dead `.empty-state:not(:has(h3))::before` CSS rule

### Wave 5: JavaScript Enhancements ✅
- ✅ **#21** Copy link shortcut 'c' already implemented; added screen reader announcement via `#sr-announce` element
- ✅ **#22** Theme toggle already has proper focus styles (global `:focus-visible` rule + `.theme-toggle:focus-visible`)
- ✅ **#23** Mini-chart bars made accessible (covered in #12 above)

### Wave 6: Print & Display Enhancements ✅
- ✅ **#24** Print stylesheet: TOC shown on print, `page-break-inside: avoid` for `pre` already present, "Printed from" footer via CSS `content`
- ✅ **#25** Breadcrumb added to `index.html` (site title only) and `search.html` (Home / Search: {query})
- ✅ **#26** Reading time in post hero styled as `.reading-time-badge` with accent-colored pill badge

### Wave 7: Future Enhancements ✅
- ✅ **#27** Request timeout documented in DEPLOY.md (Granian, Gunicorn, nginx configuration)
- ✅ **#28** Connection pool stats (size, checked_in, checked_out, overflow) added to `/health` endpoint
- ✅ **#29** CSP-Report-Only header already implemented in `set_security_headers` when `app.debug` is True
