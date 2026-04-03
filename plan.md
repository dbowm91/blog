# Consolidated Improvement Plan

**Test Command (run after each change):**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Wave 1: Critical Bugs & Security

Items that affect correctness, security, or data integrity. Wave 1A (backend) and 1B (frontend) are parallelizable.

### Wave 1A — Backend Critical (parallelizable)

#### 1.1 Fix Test Suite — Env Vars Set Before Import
- **Priority:** Critical
- **Files:** `tests/conftest.py`
- **Problem:** 210 tests error with `RuntimeError: SECRET_KEY is required` because `config.py` reads environment variables at module import time, but the `app` fixture sets them inside the fixture function. The `SECRET_KEY` and `ADMIN_PASSWORD` constants are cached at module load, so setting `os.environ` inside the fixture doesn't retroactively update them.
- **Fix:** Move `os.environ["SECRET_KEY"] = "test-secret-key"` and `os.environ["ADMIN_PASSWORD"] = "test-password"` to the very top of `conftest.py`, before any application imports. Remove the duplicate env var setup from inside the `app` fixture.
- **Test:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v` — all tests should pass.
- **Status:** ✅ DONE

#### 1.2 Add Bounds to In-Memory Caches
- **Priority:** Critical
- **Files:** `app/cache.py`, `app/routes/admin/__init__.py`
- **Problem:** `_TAG_COUNTS_CACHE` stores a single entry (no size issue), but `_analytics_cache` in admin is an unbounded dict keyed by `days` parameter. Over time, if many different `days` values are queried, the dict grows without limit.
- **Fix:** Add `_ANALYTICS_MAX_SIZE = 16` to analytics cache. On write, if size exceeds max, evict oldest entry (LRU). Document that multi-worker deployments should use external caching.
- **Test:** Verify cache expires after TTL and doesn't grow beyond max size.
- **Status:** ✅ DONE

#### 1.3 Analytics Cache Invalidation + Missing Tag Cache Invalidation
- **Priority:** High
- **Files:** `app/routes/admin/__init__.py`, `app/routes/admin/posts.py`
- **Problem 1:** `_analytics_cache` is never invalidated when post data changes (create, edit, delete, publish, unpublish).
- **Problem 2:** In `bulk_operations()`, the unpublish branch calls `sync_fts()` but does NOT call `invalidate_tag_cache()`. Tag counts in the sidebar will show stale data after bulk unpublish.
- **Fix:** Add `invalidate_analytics_cache()` function. Call it alongside `invalidate_tag_cache()` wherever post data changes (`new_post`, `edit_post`, `delete_post`, all bulk branches). Fix the missing `invalidate_tag_cache()` in the bulk unpublish branch.
- **Test:** Verify analytics page reflects changes immediately after post CRUD. Verify tag counts update after bulk unpublish.
- **Status:** ✅ DONE

### Wave 1B — Frontend Critical (parallelizable with 1A)

#### 1.4 Fix Modal Focus Trap Closure Bug
- **Priority:** Critical
- **Files:** `app/static/js/main.js`
- **Problem:** The modal focus trap keydown listener is defined OUTSIDE the `forEach` loop that iterates over modals. The `modal` variable captures the last value from the loop, not the correct modal for each iteration. When multiple modals exist, Tab trapping only works correctly for the last modal. Additionally, `e.key === 'ShiftTab'` check is dead code — Shift+Tab fires `e.key === 'Tab'` with `e.shiftKey === true`.
- **Fix:** Move the keydown listener inside the `forEach` callback so each modal gets its own handler with the correct `modal` reference. Remove the redundant `|| e.key === 'ShiftTab'` check.
- **Test:** Open keyboard help modal (`?`), press Tab — focus should cycle within the modal. Press Escape — modal should close and return focus to the trigger element.
- **Status:** ✅ DONE

---

## Wave 2: High-Priority UX & Accessibility

Wave 2A (backend/route fixes) and 2B (frontend UX) are parallelizable.

### Wave 2A — Backend/Route Fixes (parallelizable)

#### 2.1 FTS5 Special Character Escaping
- **Priority:** Medium
- **Files:** `app/search.py`
- **Problem:** `search()` only escapes double quotes. FTS5 treats `"`, `*`, `:`, `-`, `NEAR`, `AND`, `OR`, `NOT` as special. Unescaped characters cause `OperationalError`, caught and falls back to LIKE — functional but degrades search quality.
- **Fix:** Add `_escape_fts_term()` helper to strip leading/trailing hyphens (negation), replace colons (column specifier), and escape double quotes. Filter empty terms after stripping.
- **Test:** Search with queries containing `-term`, `col:term`, `"phrase"`, and combinations.
- **Status:** ✅ DONE

#### 2.2 Scheduler Status Tracking
- **Priority:** Low
- **Files:** `app/scheduler.py`
- **Problem:** `_scheduler_running` is set to `True` in `init_scheduler()` but never reset to `False` on shutdown. If the scheduler crashes and the app attempts to re-initialize, the status would be inaccurate.
- **Fix:** Update the atexit shutdown handler to reset `_scheduler_running = False` before calling `scheduler.shutdown(wait=False)`.
- **Test:** No specific test needed — defensive improvement.
- **Status:** ✅ DONE

#### 2.3 Config URL Validation Enhancement
- **Priority:** Low
- **Files:** `app/config.py`
- **Problem:** `base_url` validation only checks that it starts with `http://` or `https://`. It doesn't validate the full URL structure (e.g., `https://` with no domain would pass).
- **Fix:** Use `urllib.parse.urlparse` to validate that `base_url` has both `scheme` and `netloc`.
- **Test:** Test with invalid URLs like `https://`, `http:///path`, `not-a-url`.
- **Status:** ✅ DONE

### Wave 2B — Frontend UX (parallelizable with 2A)

#### 2.4 WCAG AA Contrast Fix for Light Mode
- **Priority:** Critical
- **Files:** `app/static/css/style.css`
- **Problem:** Light theme `--text-dim: #8c959f` on `--bg: #f6f8fa` produces ~4.0:1 contrast ratio, which **fails WCAG AA** for normal text (minimum 4.5:1). Used for chart labels, media sizes, analytics table headers, trending views, metric icons, shortcut key descriptions.
- **Fix:** Change light theme `--text-dim` to `#6e7781` (~4.6:1 on `#f6f8fa`). For small text (0.7rem tag counts, 0.6rem chart labels), add `--text-dim-strong: #4b5563` (light) / `#9ca3af` (dark) and update `.tag-count`, `.chart-label`, and other small text to use it (~6.5:1 dark, ~7.4:1 light).
- **Test:** Verify with WebAIM contrast checker. Visual verification in both modes.
- **Status:** ✅ DONE (partial: `--text-dim` changed to `#6e7781`; `--text-dim-strong` already existed)

#### 2.5 Add Unsaved Changes Warning in Editor
- **Priority:** Medium
- **Files:** `app/static/js/main.js`
- **Problem:** Navigating away from the editor without submitting loses any changes not yet autosaved to localStorage.
- **Fix:** Add a `beforeunload` event listener when the editor has unsaved changes. Track "dirty" state by comparing current form values against the last saved draft in localStorage. Remove the listener on successful form submit.
- **Test:** Manual verification — navigate away after editing, confirm browser dialog appears.
- **Status:** ✅ DONE

#### 2.6 Implement Reading Progress Bar
- **Priority:** Medium
- **Files:** `app/templates/post.html`, `app/static/js/main.js`
- **Problem:** The `.reading-progress` div exists in `post.html` with CSS transition but no JavaScript driver. It's a non-functional placeholder.
- **Fix:** Add scroll tracking in the existing throttled scroll handler: calculate `scrollY / (scrollHeight - innerHeight) * 100` and update the bar's width. The element is already scoped to post pages only.
- **Test:** Open any blog post and scroll — thin gradient bar should appear at top, growing as you scroll. On homepage, nothing should change.
- **Status:** ✅ DONE

---

## Wave 3: UI Polish & Consistency

Wave 3A (CSS/visual), 3B (template/content), and 3C (admin enhancements) are all parallelizable.

### Wave 3A — CSS & Visual (parallelizable)

#### 3.1 Add Missing Color Tokens
- **Priority:** High
- **Files:** `app/static/css/style.css`
- **Problem:** Several colors are hardcoded directly in CSS rules instead of using the design token system: `#a371f7` (stat card accent shares), `#f78166` (stat card accent subscribers), `#3b2e00`/`#d4a017` (noscript warning dark mode), `#fff` (post hero title).
- **Fix:** Add `--purple: #a371f7`, `--orange: #f78166`, `--noscript-bg: #3b2e00`, `--noscript-text: #d4a017` to `:root`. Replace hardcoded values with `var()` references. Replace `#fff` in `.post-hero-title` with `var(--text)` (light theme override can be removed since `--text` already changes between themes).
- **Test:** Verify stat card accents, noscript warning, and hero title in both modes.
- **Status:** ✅ DONE

#### 3.2 Remove Duplicate `@keyframes spin`
- **Priority:** Medium
- **Files:** `app/static/css/style.css`
- **Problem:** `@keyframes spin` is defined twice (line ~1198 and line ~1374) with identical content.
- **Fix:** Remove the duplicate definition.
- **Test:** Verify bulk loading spinner and button loading spinner still animate correctly.
- **Status:** ✅ DONE

#### 3.3 Add Intermediate Breakpoint at 960px
- **Priority:** Medium
- **Files:** `app/static/css/style.css`
- **Problem:** Between 768px (mobile) and ~1100px (max container width), the 260px sticky sidebar with 48px gap makes the content area very narrow (~540px) on screens around 850-950px.
- **Fix:** Add `@media (max-width: 960px)` with `.content-layout { grid-template-columns: 1fr; gap: 32px; }` and `.sidebar { position: static; }`. Sidebar stacks below content on mid-size screens.
- **Test:** Resize to 850px — sidebar should stack below. At 961px — sidebar sticky on right. At 768px — existing mobile layout unchanged.
- **Status:** ✅ DONE

#### 3.4 Fix Empty State Pattern Inconsistency
- **Priority:** Medium
- **Files:** `app/static/css/style.css`, `app/templates/index.html`, `app/templates/admin/media.html`, `app/templates/admin/subscribers.html`
- **Problem:** `.empty-state::before` adds a mail SVG icon above content. Works for simple `<p class="empty-state">No posts yet.</p>` but conflicts with multi-line empty states that use `<div class="empty-state"><h3>...</h3><p>...</p></div>`. Also, empty state messaging is inconsistent: index.html says "Something is brewing..." while dashboard says "Create your first one."
- **Fix:** Scope `::before` to `.empty-state:not(:has(h3))` so icon only appears for simple variants (no child headings). Standardize messaging to "No posts yet. Create your first one." across all templates.
- **Test:** Dashboard with no posts: icon appears. Media/subscribers with no items: heading+paragraph without icon.
- **Status:** ✅ DONE

#### 3.5 Standardize CSS Variable Usage
- **Priority:** Medium
- **Files:** `app/static/css/style.css`
- **Problem:** Many rules use hardcoded pixel values instead of CSS variables.
- **Fix:** Add `--radius-sm: 6px` and `--space-sm-md: 12px` to `:root` and `[data-theme="light"]`. Rename existing `--space-md-sm` to `--space-sm-md`. Systematically replace hardcoded values:
  - `border-radius: 8px` → `var(--radius)`
  - `border-radius: 12px` → `var(--radius-lg)`
  - `border-radius: 6px` → `var(--radius-sm)`
  - `gap: 16px` → `var(--space-md)`
  - `gap: 48px` → `var(--space-2xl)`
  - `gap: 24px` → `var(--space-lg)`
  - `gap: 12px` → `var(--space-sm-md)`
  - `padding: 24px` → `var(--space-lg)`
  - `padding: 16px` → `var(--space-md)`
- **Caveat:** Leave `prism-okaidia.css` alone (third-party theme).
- **Test:** Visual verification in both dark and light modes.
- **Status:** ⏳ PENDING

#### 3.6 Fix Search Input Focus Layout Shift
- **Priority:** Low
- **Files:** `app/static/css/style.css`
- **Problem:** Search input expands from 200px to 260px on focus, causing layout shift on mobile.
- **Fix:** Cap the expansion: `width: 240px` on focus. On mobile (`max-width: 768px`), use `width: calc(100% - 80px)` to remove expansion.
- **Test:** Verify no layout shift on mobile.
- **Status:** ⏳ PENDING

#### 3.7 Improve Share Button Visual Hierarchy + Fix Color Flash Stacking
- **Priority:** Low
- **Files:** `app/static/css/style.css`, `app/static/js/main.js`
- **Problem:** Share buttons are plain and only show color on hover. Additionally, rapid clicks on share buttons stack multiple `setTimeout` calls, causing color flickering.
- **Fix (CSS):** Add subtle background colors matching brand colors:
  - `.share-twitter { background: rgba(29, 161, 242, 0.1); }`
  - `.share-linkedin { background: rgba(10, 102, 194, 0.1); }`
  - `.share-hn { background: rgba(255, 102, 0, 0.1); }`
  - `.share-reddit { background: rgba(255, 69, 0, 0.1); }`
  - `.share-facebook { background: rgba(24, 119, 242, 0.1); }`
- **Fix (JS):** Store timeout ID on element (`this._flashTimeout`) and clear it before setting a new one to prevent stacking.
- **Test:** Visual verification. Rapidly click share button — colors should not flicker or get stuck.
- **Status:** ✅ DONE

### Wave 3B — Template & Content (parallelizable with 3A)

#### 3.8 Add Meta Description to Tag and Search Pages
- **Priority:** Low
- **Files:** `app/templates/tag.html`, `app/templates/search.html`
- **Problem:** Post pages have meta description, but tag and search pages don't.
- **Fix:** Add `{% block meta_description %}` to tag.html (`Posts tagged with {{ tag.name }}`) and search.html (`Search results for {{ query }}`).
- **Test:** View page source to verify meta description.
- **Status:** ✅ DONE

#### 3.9 Enable Image Loading Skeleton
- **Priority:** Medium
- **Files:** `app/templates/index.html`, `app/templates/post.html`, `app/templates/_sidebar.html`
- **Problem:** The `.img-skeleton` CSS exists but is never actively used.
- **Fix:** Add `.img-skeleton` class to lazy-loaded images: `<img class="post-card-img img-skeleton" ...>`.
- **Test:** Verify skeleton animation appears before images load.
- **Status:** ✅ DONE

#### 3.10 Add Keyboard Navigation to Post Cards
- **Priority:** Medium
- **Files:** `app/templates/index.html`, `app/templates/tag.html`, `app/templates/search.html`, `app/static/js/main.js`, `app/static/css/style.css`
- **Problem:** Post cards are not keyboard-navigable.
- **Fix:** Add `tabindex="0" role="link"` to post cards. Add keydown handler for Enter/Space to click the card's link. Add `.post-card:focus-visible` CSS with outline.
- **Test:** Tab through page, verify cards are focusable and activatable.
- **Status:** ✅ DONE

#### 3.11 Add Loading Indicator on Auto-Submit Filters
- **Priority:** Low
- **Files:** `app/static/js/main.js`, `app/static/css/style.css`
- **Problem:** Status filter and date range filter auto-submit on change with no visual feedback.
- **Fix:** Add a `.loading` class before submit — reduced opacity + wait cursor. Since the page navigates away immediately, the visual cue only needs to last ~100-200ms.
- **Test:** Verify visual feedback on filter change.
- **Status:** ✅ DONE

### Wave 3C — Admin Enhancements (parallelizable with 3A and 3B)

#### 3.12 Add Bulk Form Submission Loading State
- **Priority:** Medium
- **Files:** `app/static/js/main.js`, `app/static/css/style.css`, `app/templates/admin/dashboard.html`
- **Problem:** Bulk operations submit via standard form POST, providing no visual feedback during the request.
- **Fix:** Add a hidden loading overlay that shows during bulk form submission. Use `beforeunload` event to show overlay when form is submitted. Hide overlay on page load.
- **Test:** Submit bulk operation, verify loading overlay appears.
- **Status:** ✅ DONE

#### 3.13 Add Footer to Admin Pages
- **Priority:** Low
- **Files:** `app/templates/admin/base.html`, `app/static/css/style.css`
- **Problem:** Admin pages end abruptly after content — no footer.
- **Fix:** Add a lightweight admin footer with links: View Site, RSS Feed, copyright. Add `.admin-footer` CSS.
- **Test:** Verify footer appears on all admin pages.
- **Status:** ✅ DONE

#### 3.14 Add Stat Card Trend Indicators
- **Priority:** Medium
- **Files:** `app/routes/admin/posts.py` (or relevant analytics route), `app/templates/admin/dashboard.html`
- **Problem:** The `.stat-trend` class exists in CSS but isn't used. Stat cards could show week-over-week comparison.
- **Fix:** In `dashboard()` route, calculate week-over-week view comparison. Pass `views_trend` to template. Add `<span class="stat-trend">` to stat cards.
- **Test:** Verify trend data displays correctly.
- **Status:** ✅ DONE

#### 3.15 Add Flash Message Pause on Hover
- **Priority:** Medium
- **Files:** `app/static/js/main.js`
- **Problem:** Flash messages auto-dismiss after 5 seconds with no way to pause the timer. Users who need more time to read cannot stop the dismissal.
- **Fix:** Add `mouseenter`/`mouseleave` listeners to pause and resume the auto-dismiss timer. Use `clearTimeout`/`setTimeout` pattern.
- **Test:** Trigger a flash message, hover over it — it should NOT dismiss while hovered. Move mouse away — timer resumes. Click to dismiss immediately — works as before.
- **Status:** ✅ DONE

#### 3.16 Fix Media Upload `multiple` Attribute
- **Priority:** Medium
- **Files:** `app/templates/admin/media.html`
- **Problem:** The media upload form has `multiple` on the file input, but the JavaScript only handles `files[0]`. Users can select multiple files but only the first one is uploaded.
- **Fix:** Remove the `multiple` attribute from the visible file input since the backend expects single file uploads per request.
- **Test:** Verify single file upload works. Selecting multiple files should no longer be possible.
- **Status:** ✅ DONE

#### 3.17 Add Upload Zone Fetch Error Handling
- **Priority:** High
- **Files:** `app/static/js/main.js`
- **Problem:** The upload zone `fetch()` calls (file input change and drag-and-drop) have no `.catch()` handler. If the upload fails (network error, server error, CSRF token expired), the page silently does nothing.
- **Fix:** Add `.catch()` handlers that display an error message (`.form-error`) in the upload zone and auto-dismiss after 5 seconds. Check `response.ok` in the `.then()` handler.
- **Test:** Simulate a failed upload — error message should appear and auto-dismiss. Successful uploads should continue to reload the page.
- **Status:** ✅ DONE

---

## Wave 4: Testing & Documentation

Wave 4A (new tests) and 4B (documentation) are parallelizable.

### Wave 4A — New Tests (parallelizable)

#### 4.1 Add Backup/Restore End-to-End Tests
- **Priority:** High
- **Files:** `tests/test_backup.py` (create)
- **Tasks:** Test backup creation (compressed/uncompressed), file listing, download, filename validation, restore, restore with corrupted backup, backup while DB in use.
- **Status:** ⏳ PENDING

#### 4.2 Add Multi-User Session Management Tests
- **Priority:** High
- **Files:** `tests/test_multi_user.py` (create)
- **Tasks:** Test two users logging in simultaneously, session timeout on one user while other remains active, `AdminSession` cleanup on logout, session cookie security flags.
- **Status:** ⏳ PENDING

#### 4.3 Expand Search Special Character Tests
- **Priority:** Medium
- **Files:** `tests/test_public.py`
- **Tasks:** Add tests for comma, semicolon, pipe, backslash, Unicode, empty search, very long search query (>200 chars), FTS5 special characters (`-term`, `col:term`, `"phrase"`).
- **Status:** ⏳ PENDING

#### 4.4 Add Email Failure/Retry Tests
- **Priority:** Medium
- **Files:** `tests/test_email.py`, `tests/test_newsletter.py`
- **Tasks:** Test newsletter sending with SMTP failure, reconnection after disconnect, confirmation email send failure, attempt counting, mixed success/failure in batch.
- **Status:** ⏳ PENDING

### Wave 4B — Documentation (parallelizable with 4A)

#### 4.5 Document Multi-Worker Scheduler Limitation
- **Priority:** Medium
- **Files:** `app/scheduler.py`, `DEPLOY.md`
- **Problem:** APScheduler runs in-process. With multiple workers, each runs its own scheduler. The `fcntl` file lock prevents duplicate sends on a single machine but doesn't help across machines.
- **Fix:** Document the limitation clearly. Recommend single-worker deployment for newsletter scheduling, or external scheduler (cron, Celery beat).
- **Status:** ⏳ PENDING

#### 4.6 Improve Backup Path Resolution
- **Priority:** Low
- **Files:** `backup.py`
- **Problem:** `get_db_path()` returns `"instance/blog.db"` relative to CWD, not `app.instance_path`.
- **Fix:** Add `--db` CLI argument for explicit path. Fall back to `"instance/blog.db"` for backward compatibility.
- **Status:** ⏳ PENDING

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
| FTS5 full special character escaping | Wave 2.1 covers key cases; remaining edge cases handled by LIKE fallback |
| CSV export robustness improvements | Current implementation sufficient for real-world data |
| localStorage quota handling for drafts | Edge case (5-10MB quota); can add if users report issues |
| Newsletter fake subscriber improvement | Works but brittle; low priority |
| Newsletter retry semantics refinement | Current behavior is correct by design — `all_sent=False` triggers retry with 5-attempt limit |
| Media manager directory scan optimization | Fast for typical usage (<100 files); defer until media library grows significantly |
| Test database URI isolation | Tests use temp DB with per-test table create/drop; acceptable for now |
| `busy_timeout` PRAGMA fix | Already uses `@event.listens_for(Engine, "connect")` for per-connection PRAGMA |
| `MAX_CONTENT_LENGTH` alignment | Already computed from `MAX_UPLOAD_SIZE + 1MB` |
| Newsletter SMTP reconnection cleanup | Already correct — no redundant `server.quit()` in except handler |
| Dashboard CSP nonce | No inline script in dashboard.html — all bulk JS is in main.js |
| Tag name regex | Already restricted to ASCII `[a-zA-Z0-9\s\-]` |
| `_csrf_exempt` dead code | Not present in codebase — CSRF validation in `app/csrf.py` has no exemption path |
| Select-all checkbox placement | Already in `.filter-bar`, not inside `#bulk-actions` |
| Tag page hero layout | Already outside `content-layout` grid |
| Empty state emoji | Already uses SVG background-image, not emoji content |
| Reading progress bar location | Already scoped to `post.html`, not `base.html` |
| Split admin.py into modules | Already a package with separate modules (auth, posts, subscribers, tags, etc.) |

---

## Implementation Order Summary

| Wave | Description | Status |
|------|-------------|--------|
| **1A** | Backend critical (test suite, cache bounds, analytics invalidation) | ✅ COMPLETE |
| **1B** | Frontend critical (modal focus trap) | ✅ COMPLETE |
| **2A** | Backend/Route fixes (FTS5, scheduler, config) | ✅ COMPLETE |
| **2B** | Frontend UX (contrast, editor warning, reading progress) | ✅ COMPLETE |
| **3A** | CSS & Visual (color tokens, keyframes, breakpoint, empty states, CSS vars, search shift, share buttons) | ⚠️ PARTIAL (3.5, 3.6 pending) |
| **3B** | Template & Content (meta desc, image skeleton, keyboard nav, filter loading) | ✅ COMPLETE |
| **3C** | Admin Enhancements (bulk loading, footer, trends, flash pause, media upload, upload errors) | ✅ COMPLETE |
| **4A** | New Tests (backup, multi-user, search, email) | ⏳ PENDING |
| **4B** | Documentation (scheduler docs, backup path) | ⏳ PENDING |

**Waves 1–4 can be executed in parallel within each wave. Waves must be completed in order (1 → 2 → 3 → 4) since later waves may depend on earlier fixes (e.g., tests in Wave 4 depend on test suite fix in Wave 1.1).**

---

## Summary of Completed Items

### Wave 1 ✅
- **1.1** Test suite env vars — DONE (before this session)
- **1.2** Cache bounds — DONE (before this session)
- **1.3** Analytics cache invalidation + tag cache in unpublish — DONE
- **1.4** Modal focus trap bug — DONE

### Wave 2 ✅
- **2.1** FTS5 special character escaping — DONE
- **2.2** Scheduler status tracking — DONE
- **2.3** Config URL validation — DONE
- **2.4** WCAG AA contrast fix — DONE (partial)
- **2.5** Unsaved changes warning — DONE (before this session)
- **2.6** Reading progress bar — DONE

### Wave 3 ⚠️
- **3.1** Color tokens — DONE (before this session)
- **3.2** Duplicate @keyframes spin — DONE
- **3.3** 960px breakpoint — DONE
- **3.4** Empty state pattern — DONE
- **3.5** CSS variable standardization — PENDING
- **3.6** Search input focus shift — PENDING
- **3.7** Share button visual hierarchy — DONE (before this session)
- **3.8** Meta descriptions — DONE (before this session)
- **3.9** Image loading skeleton — DONE (before this session)
- **3.10** Post card keyboard nav — DONE (before this session)
- **3.11** Auto-submit filter loading — DONE (before this session)
- **3.12** Bulk form loading overlay — DONE (before this session)
- **3.13** Admin footer — DONE (before this session)
- **3.14** Stat card trend indicators — DONE (before this session)
- **3.15** Flash message pause on hover — DONE
- **3.16** Media upload multiple attribute — DONE
- **3.17** Upload zone fetch error handling — DONE

### Wave 4 ⏳
- **4.1-4.4** Tests — PENDING
- **4.5-4.6** Documentation — PENDING

(End of file - 337 lines)