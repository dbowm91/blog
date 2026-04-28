# Batch 2 Plans Summary

This document consolidates the contents of Plans 6-9, covering syndication improvements, frontend usability, admin panel usability, and general codebase improvements.

---

## Plan 6: Syndication Improvements Plan

### Main Objectives/Tasks
1. **JSON Feed (`/feed.json`)** — Implement JSON Feed format (version 1.1) as a modern alternative to XML-based feeds
2. **RSS Feed Enhancements** — Add `content:encoded`, author info, categories/tags, and image enclosures to RSS 2.0
3. **Conditional GET Support** — Implement `If-Modified-Since` and `ETag` handling to return `304 Not Modified` when content is unchanged
4. **Cache Headers** — Add `Cache-Control`, `Last-Modified`, and `ETag` headers for feed caching
5. **Atom Feed (`/atom`)** — (Optional/Medium) Add Atom format as a standardized RSS alternative
6. **Tag-Specific RSS Feeds** — (Optional/Medium) Allow filtered RSS feeds by tag (e.g., `/tag/python/rss`)
7. **WebSub/PubSubHubbub** — (Skipped) Low adoption, adds complexity
8. **Ping Services** — (Skipped) Obsolete protocol, minimal SEO benefit

### Implementation Details
- JSON Feed spec requires: `version`, `title`, `items` array; optional: `home_page_url`, `feed_url`, `description`, `authors`, `language`
- Item fields: `id` (URL), `url`, `title`, `content_html`, `summary`, `image`, `date_published`, `tags`, `attachments`
- RSS enhancements use `xmlns:content` namespace with `<content:encoded>` CDATA-wrapped elements
- Conditional GET uses `func.max(Post.updated_at)` query, timestamp-based strong ETag
- Cache headers: `Cache-Control: public, max-age=86400, s-maxage=604800, stale-while-revalidate=3600`

### Dependencies/Ordering
1. JSON Feed first (standalone, no dependencies)
2. RSS Enhancements + Conditional GET + Cache Headers combined into single `rss.py` refactor
3. Atom Feed (optional, low-effort)
4. Tag-Specific RSS (requires RSS refactor first)

### Phase/Wave Organization
- **Phase 1 (High Priority)**: JSON Feed + RSS refactor with all enhancements + base.html autodiscovery links
- **Phase 2 (Medium Priority)**: Atom Feed + Tag-Specific RSS
- **Phase 3 (Skip)**: WebSub, Ping Services

---

## Plan 7: Frontend Usability Improvement Plan

### Main Objectives/Tasks
**High Priority (4 items):**
- H1: Search experience enhancements (autocomplete, FTS5 prefix index, recent searches via localStorage)
- H2: Client-side form validation (self-host `formageddon` library, add HTML5 attributes)
- H3: Editor preview latency reduction (self-host MiniGFM for client-side markdown rendering)
- H4: Bulk operation feedback enhancement (action-specific overlay text with item count)

**Medium Priority (4 items):**
- M1: Public toast notifications (add `showToast()` call to share.js)
- M2: SVG icon accessibility (add `aria-hidden="true"` and `role="img"` + `aria-label`)
- M3: Color contrast fixes (increase badge background alpha, darken border color)
- M4: Keyboard shortcut discoverability (add `title` attribute, first-visit toast hint)

**Low Priority (4 items):**
- L1: Remove stat card hover effects (non-interactive cards with false affordance)
- L2: Reading progress bar toggle (localStorage-based show/hide)
- L3: Fix flash message flicker (hide `.flash-container` immediately when JS enabled)
- L4: Mobile share button "More" menu (dropdown for hidden social buttons)

### Implementation Details
- FTS5 prefix index: `prefix=2 3 4` added to `posts_fts` virtual table
- New endpoint `/api/search/suggestions` returns JSON array of matching post titles
- Formageddon (4.2KB) for client-side validation with `showToast()` integration
- MiniGFM (~3KB) for client-side markdown parsing, reduces debounce from 300ms to 150ms
- Bulk feedback shows "Publishing 3 post(s)..." style messages
- CSS changes: `--border` darken to `#b0b8c2`, badge alpha 0.15 → 0.25

### Dependencies/Ordering
1. L3 (Flash flicker fix) — 2 lines CSS, 5 min — no dependencies
2. L1 (Stat card hover) — delete CSS block, 5 min
3. M2 (SVG accessibility) — add aria-hidden, 15 min
4. M3 (Color contrast) — update CSS vars, 10 min
5. M1 (Public toasts) — 1-line change, 5 min
6. M4 (Keyboard hint) — add toast hint, 20 min
7. H4 (Bulk feedback) — update JS, 15 min
8. H2 (Form validation) — download lib + update forms, 45 min
9. H3 (Editor preview) — download lib + update JS, 30 min
10. H1 (Search enhancements) — new endpoint + JS, 60 min
11. L2 (Progress toggle) — new JS module, 30 min
12. L4 (Mobile share menu) — new dropdown, 45 min

H1 (Search) depends on FTS5 prefix index being added first.

### Phase/Wave Organization
Implementation order follows effort-vs-impact optimization, starting with simplest fixes (L3, L1) before medium and high priority items.

---

## Plan 8: Admin Panel Usability Improvement Plan

### Main Objectives/Tasks
**High Priority (2 items):**
1. Add Pages link to admin navigation (routes exist, link missing from "More" dropdown)
2. Style Restore Backup button as destructive action (distinct from Delete despite higher risk)

**Medium Priority (7 items):**
3. Add active state highlighting for nested nav items (use `startswith` for settings/posts)
4. Replace blocking `confirm()` dialog with accessible modal (`showConfirmModal` promise-based)
5. Refactor Users page inline forms to reduce clutter (modal-based actions)
6. Fix mobile editor preview toggle bug (class name mismatch JS vs CSS)
7. Add focus trapping to confirm modals (Tab cycles within modal, Escape closes)
8. Add dynamic ARIA labels to confirm modals (add `aria-describedby`)
9. Improve bulk action loading state (disable buttons, timeout handling, error handling)

**Low Priority (3 items):**
10. Regroup "More" dropdown navigation items (add separator between Content and System groups)
11. Improve tag rename UX (Escape handler cancels, slug preview shows while typing)
12. Show post status/slug as compact badges on mobile (remove dead CSS)

### Implementation Details
- Pages link added after Tags in dropdown using `url_for('admin.pages_list')`
- `.btn-restore` class added with red background, white text, warning icon
- Active state uses endpoint matching: `request.endpoint.startswith('admin.settings')`
- `showConfirmModal()` returns Promise, stores previousActiveElement for focus restoration
- Focus trap uses focusableSelectors list, Tab/Shift+Tab cycling
- Bulk loading: disable submit buttons, set "Processing..." text, 30s timeout
- Tag rename: `oninput="previewTagSlug(this)"` shows live slug preview

### Dependencies/Ordering
| Step | Item | Est. Time | Dependencies |
|------|------|-----------|--------------|
| 1 | #1 Pages link | 5 min | None |
| 2 | #2 Restore styling | 10 min | None |
| 3 | #3 Active state | 15 min | After #1 |
| 4 | #8 ARIA labels | 2 min | None |
| 5 | #6 Editor toggle bug | 10 min | None |
| 6 | #9 Bulk loading | 20 min | None |
| 7 | #4 Confirm modal | 30 min | After #8 |
| 8 | #7 Focus trap | 25 min | After #4 |
| 9 | #5 Users forms | 45 min | None |
| 10 | #11 Tag UX | 15 min | None |
| 11 | #10 Dropdown grouping | 10 min | None |
| 12 | #12 Dead CSS | 5 min | None |

**Total estimated time**: ~2.5 hours

### Phase/Wave Organization
Steps numbered in implementation order above. No explicit phases; ordered by dependencies and complexity.

---

## Plan 9: Codebase Improvement Plan

### Main Objectives/Tasks
**Priority 1 - High (Testing Coverage Gaps):**
- 1.1: Add missing tests for untested admin features (~20 new tests: Static Pages CRUD, Site Settings/Theme, Password Reset Flow, Post Revisions, Session Management, Scheduler Status)
- 1.2: Add session fixation prevention test (verify `session.clear()` before `login_user()`)
- 1.3: Fix flaky upload test (async timing issue in `test_upload_browse_delete_image`)

**Priority 2 - Medium (Testing Infrastructure):**
- 2.1: Configure pytest-cov for coverage measurement (target 75% initially, 85% after Priority 1)
- 2.2: Refactor duplicate fixtures (consolidate into `conftest.py`)

**Priority 3 - Low-Medium (Refactoring):**
- 3.1: Extract THEME_PRESETS from models.py (92 lines of config data → `app/theme_presets.py`)
- 3.2: Split public.py into package (`app/routes/public/` with blog.py, search.py, subscribe.py, share.py, sitemap.py, health.py, helpers.py)

**Priority 4 - Low (PostgreSQL Migration Preparation):**
- 4.1: Add Alembic SQLite batch mode (add `render_as_batch=True` for SQLite)
- 4.2: Create database dialect detection utility (`get_db_dialect()`)
- 4.3: Update health check for PostgreSQL compatibility (replace `sqlite_master` query)
- 4.4: Create PostgreSQL search module (future-ready FTS implementation)

**Priority 5 - Low (APScheduler):** SKIP — current approach sufficient
**Priority 6 - Low (File Uploads):** SKIP — local storage optimal at current scale

### Implementation Details
- New test files: `tests/test_pages.py`, `tests/test_settings.py`, `tests/test_revisions.py`, `tests/test_sessions.py`, `tests/test_scheduler.py`
- Session fixation test uses `client.session_transaction()` to verify session clearing
- Flaky test fix: replace `time.sleep(0.5)` with `expect(page.locator()).to_be_visible(timeout=5000)`
- pytest.ini configuration: `addopts = --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=75`
- THEME_PRESETS extraction: 92-line dict moved to `app/theme_presets.py`, updated imports in settings.py and context_processors.py
- public.py split follows admin blueprint pattern in `app/routes/admin/__init__.py`

### Dependencies/Ordering
| Phase | Items | Estimated Time | Dependencies |
|-------|-------|----------------|-------------|
| Phase 1 | 1.1, 1.2 | 5-7 hours | None |
| Phase 2 | 1.3, 2.1, 2.2 | 2-3 hours | Phase 1 |
| Phase 3 | 3.1, 3.2 | 4-5 hours | None (can parallel with Phase 1) |
| Phase 4 | 4.1-4.4 | 5-7 hours | None (future-ready, can defer) |
| Phase 5 | 5.1, 6.1 | Skip | N/A |

**Total estimated time for recommended items**: 11-15 hours

### Phase/Wave Organization
- **Phase 1**: Core testing gaps
- **Phase 2**: Test infrastructure improvements (depends on Phase 1)
- **Phase 3**: Refactoring (can run parallel to Phase 1)
- **Phase 4**: PostgreSQL prep (future-ready, deferrable)
- **Phase 5**: Skip items

---

## Cross-Plan Summary

### Files Requiring Changes

| File | Plans |
|------|-------|
| `app/routes/rss.py` | 6 |
| `app/templates/base.html` | 6 |
| `app/templates/tag.html` | 6 |
| `app/static/css/style.css` | 7, 8 |
| `app/search.py` | 7 |
| `app/routes/public.py` | 7, 9 |
| `app/templates/search.html` | 7 |
| `app/static/js/public/search.js` (new) | 7 |
| `app/static/js/lib/formageddon.js` (new) | 7 |
| `app/static/js/lib/minigfm.min.js` (new) | 7 |
| `app/static/js/shared/validation.js` (new) | 7 |
| `app/static/js/admin/editor.js` | 7, 8 |
| `app/static/js/admin/bulk.js` | 7, 8 |
| `app/static/js/admin/shortcuts.js` | 7, 8 |
| `app/static/js/public/share.js` | 7 |
| `app/static/js/shared/reading-progress-toggle.js` (new) | 7 |
| `app/templates/_post_content.html` | 7 |
| `app/templates/_sidebar.html` | 7 |
| `app/templates/admin/base.html` | 8 |
| `app/templates/admin/backup.html` | 8 |
| `app/templates/admin/users.html` | 8 |
| `app/templates/admin/tags.html` | 8 |
| `app/templates/admin/dashboard.html` | 8 |
| `app/static/js/shared/utils.js` | 8 |
| `tests/test_pages.py` (new) | 9 |
| `tests/test_settings.py` (new) | 9 |
| `tests/test_auth.py` | 9 |
| `tests/test_revisions.py` (new) | 9 |
| `tests/test_sessions.py` (new) | 9 |
| `tests/test_scheduler.py` (new) | 9 |
| `app/theme_presets.py` (new) | 9 |
| `app/routes/public/` (new package) | 9 |
| `migrations/env.py` | 9 |
| `app/utils.py` | 9 |
| `app/search_postgres.py` (new) | 9 |
| `pytest.ini` | 9 |

### Items to Skip (Consensus)
- **WebSub/PubSubHubbub** (Plan 6) — Low adoption
- **Ping Services** (Plan 6) — Obsolete protocol
- **Scheduler health check enhancement** (Plan 9) — Current approach sufficient
- **Storage abstraction layer** (Plan 9) — Local storage optimal at current scale
- **Rate limiting** (Plan 9) — Reverse proxy approach correct

### Priority Ordering Across All Plans
1. JSON Feed + RSS enhancements (Plan 6) — High
2. Missing admin tests (Plan 9) — High
3. Search enhancements (Plan 7 H1) — High
4. Form validation (Plan 7 H2) — High
5. Editor preview (Plan 7 H3) — High
6. Bulk feedback (Plan 7 H4) — High
7. Pages link + Restore button (Plan 8 #1-2) — High
8. Confirm modal + Focus trap (Plan 8 #4, #7) — Medium
9. Medium usability items (Plan 7 M1-M4, Plan 8 #3, #5-6, #8-9) — Medium
10. Refactoring (Plan 9 #3.1-3.2) — Low-Medium
11. PostgreSQL prep (Plan 9 #4.1-4.4) — Low (future-ready)
12. Low priority fixes (Plan 7 L1-L4, Plan 8 #10-12) — Low
