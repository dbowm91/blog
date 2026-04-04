# Improvement Plan

Consolidated from codebase and UI reviews. Organized into parallelizable waves. Items within each wave can be worked on simultaneously by sub-agents unless noted otherwise.

---

## Wave 1: Critical Bugs (Fix First)

### 1. Missing `logger` import in session timeout handler

**File:** `app/__init__.py:226`
**Problem:** The `before_request_handler` references `logger.warning()` when failing to delete an expired admin session, but `logger` is never imported in this module. This will raise `NameError` at runtime whenever a session expires and the DB delete fails.
**Impact:** Unhandled exception on session expiry → 500 error for the user.
**Fix:** Add `logger = logging.getLogger(__name__)` near the top of the file, or use `app.logger.warning()` instead (already available via Flask).
**Estimated effort:** 2 minutes
**Risk:** Very low — pure import fix.

### 2. Redundant `db.session.commit()` and `db.session.expire_all()` at startup

**File:** `app/__init__.py:366-367`
**Problem:** After the user creation/FTS init blocks (both of which commit or rollback internally), lines 366-367 call `db.session.commit()` and `db.session.expire_all()` unconditionally. At this point the session is already clean, so these are no-ops. However, if `init_fts()` fails silently and rolls back, the outer commit could theoretically commit unintended changes.
**Impact:** Low — unlikely to cause issues in practice, but violates the principle of explicit transaction boundaries.
**Fix:** Remove lines 366-367. Each inner block already handles its own commit/rollback.
**Estimated effort:** 2 minutes
**Risk:** Very low — the inner blocks already handle their own commits.

### 3. Share tracking is fire-and-forget on `<a>` elements

**Files:** `app/templates/post.html:52-69`, `app/static/js/main.js:133-168`
**Problem:** The share bar has 6 `<a>` elements and 1 `<button>` (Copy). The JS click handler fires a `fetch()` to `/api/track-share` but does NOT call `e.preventDefault()`. The browser navigates to the share URL immediately, and the `fetch()` is fire-and-forget with `keepalive: true`. This is unreliable — `keepalive` is not supported in all browsers for cross-origin navigations.
**Impact:** Share counts are silently undercounted.
**Fix:** Use `navigator.sendBeacon()` for tracking (designed for this exact scenario). Fall back to `fetch(keepalive: true)` if `sendBeacon` is unavailable.
**Estimated effort:** 10 minutes
**Risk:** Low — only affects tracking, doesn't change share link behavior.

### 4. Duplicate select-all/bulk logic between `main.js` and `subscribers.html`

**Files:** `app/static/js/main.js:549-578`, `app/templates/admin/subscribers.html:76-106`
**Problem:** Both files implement select-all and bulk UI toggle logic. They work independently and can conflict. If both fire on the same checkbox change event, the bulk actions bar may flicker or behave unpredictably. The inline script also adds a second event listener to every `.bulk-checkbox` on the subscribers page.
**Impact:** Redundant code, potential race conditions, maintenance burden.
**Fix:** Move the screen reader announcement from the inline script into `main.js`'s `updateBulkActions()` function. Remove the entire inline `<script>` block from `subscribers.html`. Add a `data-bulk-select` attribute to the subscribers `#bulk-form` so `main.js` knows to use the generic handler.
**Estimated effort:** 30 minutes
**Risk:** Low — the generic handler in main.js already works for dashboard; extending it to subscribers is straightforward.

---

## Wave 2: Backend Improvements

### 5. Replace raw SQL `db.text()` with `db.case()` for FTS result ordering

**File:** `app/routes/public.py:207-210`
**Problem:** The CASE expression for preserving FTS result order is built via string interpolation. While `post_ids` are validated as integers, this is still a SQL injection surface if the validation ever regresses.
**Fix:** Use SQLAlchemy's `case()`:
```python
from sqlalchemy import case
order_expr = case({pid: n for n, pid in enumerate(post_ids)}, value=Post.id)
```
Then use `.order_by(order_expr)` instead of `db.text(...)`.
**Estimated effort:** 15 minutes
**Risk:** Low — functionally equivalent, safer.

### 6. Make `_scheduler_running` flag thread-safe

**File:** `app/scheduler.py:28`
**Problem:** The global `_scheduler_running` boolean is read/written from multiple threads without synchronization. In practice it's only set once at startup and read for health checks, but it's technically a data race.
**Fix:** Use a `threading.Event`:
```python
_scheduler_running = threading.Event()
# set() on init, clear() on shutdown, is_set() for status checks
```
**Estimated effort:** 10 minutes
**Risk:** Low — internal status flag only.

### 7. Refactor `_create_post_object` and `_commit_post_with_rollback` to use kwargs

**File:** `app/routes/admin/posts.py:160-206`
**Problem:** Both functions take 8-9 positional arguments, making calls error-prone and hard to read.
**Fix:** Convert to keyword-only arguments:
```python
def _create_post_object(*, title, body, summary, published, image, now, scheduled_publish_at, tag_names):
```
**Estimated effort:** 20 minutes
**Risk:** Low — internal helpers only, callers are in the same file.

### 8. Subscribe retry path doesn't check `expires_at` for unconfirmed subscribers

**File:** `app/routes/public.py:373-386`
**Problem:** When a concurrent subscribe request hits the `IntegrityError` path and re-queries the existing subscriber, it only checks `existing.confirmed`. If the subscriber is unconfirmed but their `expires_at` has passed, the code resets the token and sends another confirmation email instead of treating them as expired.
**Impact:** Expired unconfirmed subscribers get their tokens reset and receive duplicate confirmation emails on concurrent subscribe attempts.
**Fix:** Add an `expires_at` check before resetting the token. If expired, delete the subscriber and fall through to create a fresh one.
**Estimated effort:** 20 minutes
**Risk:** Low — edge case with concurrent requests. Add a test for this scenario.

### 9. Dashboard queries are not cached

**File:** `app/routes/admin/posts.py:43-157`
**Problem:** Every dashboard hit runs ~10 aggregate queries (view counts, share counts, trending, subscriber stats, etc.). The analytics page has a 5-minute cache but the dashboard doesn't.
**Impact:** Dashboard becomes slow with large datasets.
**Fix:** Reuse `_get_analytics_data()` from helpers for the dashboard metrics, or add a lightweight cache with a 2-3 minute TTL.
**Estimated effort:** 1-2 hours
**Risk:** Medium — need to ensure cache invalidation on post CRUD.

---

## Wave 3: Template & Frontend Refactoring

### 10. Refactor `post.html` to use `_post_content.html` partial

**Files:** `app/templates/post.html:24-123`, `app/templates/_post_content.html`
**Problem:** The article markup (hero, share bar, TL;DR, body, author card, footer) is duplicated between `post.html` and `_post_content.html`. Changes to the hero, author card, or body structure must be made in two places.
**Fix:** Restructure `_post_content.html` to accept a `show_full_share` flag, then include it from `post.html`. The following stay in `post.html`: breadcrumb, reading progress bar, TOC container, related posts, lightbox. The following move into `_post_content.html` (controlled by `show_full_share`): hero image, share bar, TL;DR, body, author card, post footer.
**Estimated effort:** 1-2 hours
**Risk:** Medium — template refactoring. Need to verify all context variables are available in both contexts.

### 11. Consolidate 404/500 error pages into shared partial

**Files:** `app/templates/404.html`, `app/templates/500.html`
**Problem:** Both files are structurally identical — only the error code, title, and message differ.
**Fix:** Create `app/templates/_error.html` partial with `error_code`, `error_title`, `error_message` variables. Simplify both error pages to set these variables and include the partial.
**Estimated effort:** 15 minutes
**Risk:** Low — purely cosmetic refactoring.

### 12. Move search accessibility announcement to `main.js`

**File:** `app/templates/search.html:65-74`
**Problem:** Inline `<script>` block announces search results to screen readers. While it has a CSP nonce, it breaks the pattern of keeping all JS in `main.js`.
**Fix:** Add a `data-search-announce` attribute to the search results container. Add a handler in `main.js` that reads the count element and announces it. Remove the inline `<script>` from `search.html`.
**Estimated effort:** 10 minutes
**Risk:** Low — same behavior, just relocated.

### 13. Add `.form-help` CSS class

**File:** `app/templates/admin/tags.html:17`
**Problem:** Uses `<p class="form-help">` but no CSS rule exists in `style.css`. Renders as a plain paragraph with no visual distinction.
**Fix:** Add to `style.css`:
```css
.form-help {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-top: var(--space-xs);
    margin-bottom: var(--space-md);
}
```
**Estimated effort:** 5 minutes
**Risk:** None.

### 14. Add loading states for all admin forms

**File:** `app/static/js/main.js:592-602`
**Problem:** Only `form.editor-form` gets disabled buttons + "Saving..." text on submit. Other admin forms (create user, create tag, create backup, login) don't get loading states, allowing double-submissions.
**Fix:** Extend the loading state handler to cover all admin forms with a `data-loading` attribute. Add `data-loading` to admin forms that need it. Use `data-loading-text` for custom text.
**Estimated effort:** 30 minutes
**Risk:** Low — additive change, doesn't affect existing behavior.

### 15. Fix admin nav dropdown overflow on narrow viewports

**File:** `app/static/css/style.css` (dropdown rules)
**Problem:** The admin "More" dropdown is positioned `top: 100%; right: 0` with `min-width: 140px`. On very narrow viewports (e.g., 320px phones), it can extend beyond the left edge of the viewport.
**Fix:** Use `max-width: min(200px, calc(100vw - 32px))` to ensure it stays within bounds.
**Estimated effort:** 10 minutes
**Risk:** Low.

---

## Wave 4: Polish & Low Priority

### 16. Fix `SECRET_KEY` fallback inconsistency

**File:** `app/config.py:72`
**Problem:** `_env("SECRET_KEY")` returns `None` if not set, but the AGENTS.md docstring says "falls back to empty string." The check in `__init__.py` (`if not SECRET_KEY`) catches both, but it's inconsistent.
**Fix:** Change to `_env("SECRET_KEY", "")` for consistency, or update documentation.
**Estimated effort:** 2 minutes
**Risk:** None.

### 17. Remove redundant local `import uuid` in `_generate_unique_slug`

**File:** `app/routes/admin/helpers.py:227`
**Problem:** `uuid` is already imported at module level (line 10). The local import shadows it unnecessarily.
**Fix:** Delete the local `import uuid` line.
**Estimated effort:** 1 minute
**Risk:** None.

### 18. Fix quote style inconsistency in `csrf.py`

**File:** `app/csrf.py:24`
**Problem:** Uses single quotes (`'TESTING'`, `'CSRF_ENABLED'`) while the rest of the codebase uses double quotes.
**Fix:** Change to double quotes for consistency.
**Estimated effort:** 1 minute
**Risk:** None.

### 19. Media listing loads all files into memory before pagination

**File:** `app/routes/admin/media.py:22-37`
**Problem:** `os.scandir()` reads all files, builds a list of dicts, sorts it, then slices for pagination. With `MEDIA_MAX_FILES=1000` this is fine, but the sort happens before truncation.
**Fix:** Use `heapq.nlargest()` or sort-then-slice more efficiently.
**Estimated effort:** 30 minutes
**Risk:** Low — cosmetic improvement for current file counts.

### 20. `func.cast(Subscriber.confirmed, db.Integer)` is SQLite-specific

**File:** `app/routes/admin/helpers.py:158`
**Problem:** Casting a boolean to integer via `func.cast(..., db.Integer)` works for SQLite but wouldn't port to PostgreSQL/MySQL without changes.
**Fix:** Use `Subscriber.confirmed.cast(db.Integer)` or a database-agnostic approach. Document the SQLite dependency.
**Estimated effort:** 10 minutes
**Risk:** Low — app is SQLite-only per design.

### 21. Fix lightbox visibility pattern

**File:** `app/templates/post.html:125`, `app/static/js/main.js:832-890`, `app/static/css/style.css:883-910`
**Problem:** The lightbox uses CSS `opacity: 0; visibility: hidden` as default state, then `.open` class toggles to `opacity: 1; visibility: visible`. This is inconsistent with the modal pattern which uses `.hidden` (`display: none !important`).
**Fix:** Add `.hidden` as the initial state for CSP-compliant rendering. Update JS to remove `.hidden` first, then use `requestAnimationFrame` to add `.open` (triggers CSS transition).
**Estimated effort:** 10 minutes
**Risk:** Low — verify lightbox open/close still works smoothly.

### 22. Fix mobile nav separator styling

**File:** CSS for `.nav-separator` in `app/static/css/style.css`
**Problem:** On mobile, `.nav-separator` becomes a full-width horizontal rule. The admin nav has separators between logical groups that look like full-width dividers in a vertical menu, which is visually heavy.
**Fix:** Reduce the visual weight of separators in mobile nav with reduced opacity.
**Estimated effort:** 5 minutes
**Risk:** None.

### 23. Ensure theme toggle has proper focus styles

**File:** `app/static/js/main.js` (dynamic creation), `app/static/css/style.css` (`.theme-toggle` rules)
**Problem:** The theme toggle button is dynamically created and inserted into `.nav-links`. It has hover styles but should be verified to inherit the global `:focus-visible` outline properly.
**Fix:** Verify the global `:focus-visible` rule applies to `.theme-toggle`. If not, add explicit focus styles.
**Estimated effort:** 5 minutes
**Risk:** Low.

### 24. Add `prefetch` hint for pagination links specifically

**File:** `app/static/js/main.js:925-944`
**Problem:** The existing prefetch handler triggers on `mouseenter` for ALL links with a 100ms delay. It would be more efficient to prioritize pagination links (next/previous page) since those are the most likely next destinations.
**Fix:** Add explicit pagination prefetching with higher priority (no delay) for `.page-link` elements. The existing generic handler will still catch other links on hover.
**Estimated effort:** 10 minutes
**Risk:** Low — prefetch is a hint, not a guarantee.

### 25. Improve empty state for search with no results

**Files:** `app/templates/search.html:44-48`, `app/templates/admin/dashboard.html:126-129`
**Problem:** When search returns no results, the empty state shows a generic message. Could be more helpful by suggesting actions.
**Fix:** Enhance the search empty state with a link to browse all posts.
**Estimated effort:** 5 minutes
**Risk:** None.

---

## Wave 5: Future Enhancements

### 26. Add rate limiting documentation to DEPLOY.md

**Problem:** AGENTS.md explicitly says "Do not add rate limiting code to this project" and recommends proxy-level rate limiting. The DEPLOY.md should include concrete rate limiting examples for common proxies (nginx, Caddy, Cloudflare).
**Fix:** Add a "Rate Limiting" section to DEPLOY.md with copy-paste configs.
**Estimated effort:** 30 minutes

### 27. Add request timeout middleware

**Problem:** No request timeout is configured. Long-running requests (e.g., large file uploads, slow DB queries) could tie up worker threads.
**Fix:** Add a `before_request` timeout check or configure at the WSGI/ASGI server level (Granian/gunicorn).
**Estimated effort:** 30 minutes

### 28. Add database connection pool monitoring

**Problem:** No visibility into SQLite connection pool state. If the pool is exhausted, requests will hang until the busy_timeout fires.
**Fix:** Log pool stats periodically or expose via the `/health` endpoint.
**Estimated effort:** 1 hour

### 29. Consider adding `Content-Security-Policy-Report-Only` header

**Problem:** CSP violations are silently blocked. A report-only header would help detect issues during development.
**Fix:** Add `Content-Security-Policy-Report-Only` with a report-uri when `app.debug` is True.
**Estimated effort:** 30 minutes

### 30. Add print stylesheet improvements

**File:** `app/static/css/style.css:3161-3231`
**Problem:** The existing print stylesheet is good but could be enhanced: page break controls for long code blocks, print the reading time and author info, add a "Printed from {site_url}" footer.
**Fix:** Extend the print stylesheet with additional rules.
**Estimated effort:** 30 minutes

### 31. Add skeleton loading for dashboard post list

**File:** `app/templates/admin/dashboard.html`
**Problem:** Dashboard loads synchronously — no loading state while the page renders. With many posts and analytics queries, this can feel slow.
**Fix:** Add skeleton placeholders that show immediately, then get replaced when content loads. Use CSS shimmer animation.
**Estimated effort:** 1-2 hours

### 32. Add keyboard navigation for share buttons

**File:** `app/templates/post.html:50-73`
**Problem:** Share buttons are navigable via Tab, but there's no keyboard shortcut to activate common share actions (e.g., `c` for copy link).
**Fix:** Add a `title` attribute with keyboard hint to the copy button. Add a JS handler (guarded to post pages) that listens for `c` key press when not in an input.
**Estimated effort:** 15 minutes

---

## Execution Order

| Wave | Items | Estimated Total | Priority |
|------|-------|-----------------|----------|
| 1 | #1-#4 | 45 min | Critical — bugs that cause errors or data loss |
| 2 | #5-#9 | 2.5 hours | Medium — backend improvements |
| 3 | #10-#15 | 2.5 hours | Medium — template & frontend refactoring |
| 4 | #16-#25 | 1.5 hours | Low — polish & consistency |
| 5 | #26-#32 | 4 hours | Future — nice-to-have features |

## Parallelization Guide

Items within each wave can be worked on in parallel by sub-agents, with these dependencies:

- **Wave 2:** #9 (dashboard caching) should be done after #7 (helper cleanup) since they touch the same files.
- **Wave 3:** #10 (partial refactor) should be done before any other changes to `post.html` or `_post_content.html`. #12 (search announcement) and #14 (loading states) both touch `main.js` but are in different sections — can be parallelized safely.
- **Wave 4:** All items are independent and can be fully parallelized.

## Testing Strategy

- **Wave 1:** Run existing test suite — no new tests needed for #1, #2. Manual testing of share tracking (#3) and bulk select on both dashboard and subscribers pages (#4).
- **Wave 2:** Add regression tests for #5 (SQL injection prevention), #8 (concurrent subscribe edge case). Run existing tests for #6, #7, #9.
- **Wave 3:** Full regression test of post page rendering, preview mode, error pages, search functionality, all admin forms.
- **Wave 4:** Visual inspection across browsers, verify lightbox open/close, check focus styles with keyboard navigation.
- **Wave 5:** Add tests for new features as they're implemented. Print preview testing, skeleton loading behavior, keyboard shortcut testing.
