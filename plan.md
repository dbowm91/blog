# Consolidated Improvement Plan

Generated from codebase review on 2026-04-01. All items verified against current code.
Supersedes plan2.md, plan3.md, plan4.md, plan5.md, plan6.md.

Each wave builds on the previous. Sub-agents within a wave can run in parallel since they touch different files/domains.

---

## Wave 1 — Critical Bugs & Dead Code (parallelizable)

Two independent sub-agents: **Backend** and **CSS/JS**.

### Sub-Agent A: Backend Bugs

#### 1A.1 Fix `subscribers_bulk` route accepting GET

**File:** `app/routes/admin.py:704`
**Problem:** Route decorator is `@admin.route("/subscribers/bulk")` (defaults to GET-only) but reads `request.form` on line 717, which is empty on GET. Bulk operations silently do nothing.
**Fix:** Add `methods=["POST"]` to the route decorator.

#### 1A.2 Fix subscribe race condition (IntegrityError)

**File:** `app/routes/public.py:336-338`
**Problem:** Two concurrent subscribe requests with the same email both pass the `scalar_one_or_none()` check, then both try to insert. The unique constraint causes an unhandled `IntegrityError` → 500.
**Fix:** Wrap insert + commit in `try/except IntegrityError`. On collision, re-query existing subscriber and fall through to existing logic.

#### 1A.3 Fix CSV export field escaping

**Files:** `app/routes/admin.py:680-701` (`export_subscribers`), `app/routes/admin.py:741-748` (`subscribers_bulk` export)
**Problem:** CSV built with f-strings. Commas, quotes, or newlines in emails break CSV formatting. Also vulnerable to CSV formula injection.
**Fix:** Use `csv.writer` via `io.StringIO`. Optionally prefix cells starting with `=`, `+`, `-`, `@` with a single quote.

#### 1A.4 Fix orphan tag cleanup never persisting

**Files:** `app/routes/admin.py:528` (edit_post), `551` (delete_post), `1013` (bulk_operations)
**Problem:** `_cleanup_orphan_tags()` is called *after* `db.session.commit()` in all three callers. The delete operations stay in the session but are never committed — orphan tags are never actually removed.
**Fix:** Move `_cleanup_orphan_tags()` and `invalidate_tag_cache()` calls to before `db.session.commit()` in all three locations.

#### 1A.5 Fix backup restore doesn't decompress .db.gz

**File:** `app/routes/admin.py:1189-1207` (`restore_backup`)
**Problem:** Restore uses `shutil.copy2()` directly. For `.db.gz` backups, this copies compressed bytes as the SQLite database, corrupting it.
**Fix:** Check filename suffix; if `.db.gz`, decompress with `gzip` to a temp file before copying.

#### 1A.6 Fix base URL validation unreachable

**File:** `app/config.py:122-132`
**Problem:** `raise RuntimeError` fires at line 122 before the base_url check at lines 125-129. If earlier errors exist, base_url validation is never reached.
**Fix:** Move base_url validation (lines 125-129) before the first `if errors: raise` on line 122. Remove the duplicate raise on lines 131-132.

#### 1A.7 Remove unused imports

**Files:**
- `app/routes/admin.py:1` — `import csv` (unused, CSV is built with f-strings)
- `app/routes/admin.py:2` — `import io` (unused)
- `app/routes/public.py:18` — `invalidate_tag_cache` import (never called in public.py)

**Fix:** Remove unused import lines.

### Sub-Agent B: CSS/JS Dead Code

#### 1B.1 Fix mobile nav animation class mismatch

**Files:** `app/static/css/style.css:201-204` vs `app/static/js/main.js:160`
**Problem:** CSS defines `@keyframes slideInRight` on `.nav-links.active`, but JS toggles `.open`. The animation never fires. The `::before` backdrop at lines 206-213 also needs to be gated on `.nav-links.open`.
**Fix:**
- Change `.nav-links.active` to `.nav-links.open` in CSS
- Gate the `::before` backdrop on `.nav-links.open::before`

#### 1B.2 Remove duplicate prose heading sizes

**File:** `app/static/css/style.css:666-668`
**Problem:** `.prose h1/h2/h3` sizes at lines 666-668 (1.8rem/1.45rem/1.2rem) are completely overwritten by lines 671-673 (2em/1.5em/1.25em).
**Fix:** Delete lines 666-668.

#### 1B.3 Remove duplicate `.copy-code-btn` in style.css

**File:** `app/static/css/style.css:732-745`
**Problem:** `.copy-code-btn` definition is fully overridden by the more complete version in `prism-okaidia.css:112-142` (includes `font-family`, `z-index`, `focus-within`).
**Fix:** Remove lines 732-745 entirely.

#### 1B.4 Remove duplicate mobile `.post-card-body` padding

**File:** `app/static/css/style.css:2228-2230`
**Problem:** In `@media (max-width: 768px)`, padding set at line 2228 (`16px 20px`) is overwritten at line 2285 (`14px 16px`).
**Fix:** Remove lines 2228-2230.

#### 1B.5 Remove deprecated vendor prefixes

**File:** `app/static/css/prism-okaidia.css:15-17`
**Problem:** `-webkit-hyphens`, `-moz-hyphens`, `-ms-hyphens` are dead — `hyphens` has broad support, and hyphenation has no effect on `<pre>` blocks anyway.
**Fix:** Remove the three vendor-prefixed lines.

#### 1B.6 Remove orphan mobile editor CSS

**File:** `app/static/css/style.css:1214-1230`
**Problem:** References classes that don't exist in any template: `.editor-container`, `.editor-tabs`, `.tab-btn`, `.posts-grid`.
**Fix:** Remove lines 1213-1230 (verify `.sidebar { order: 1; }` still needed before removing).

---

## Wave 2 — Error Handling, Logging & JS Fixes (parallelizable)

Two independent sub-agents.

### Sub-Agent A: Error Handling & Logging

#### 2A.1 Add error handling to unguarded `db.session.commit()` calls

Multiple admin routes do `db.session.commit()` with no try/except. SQLite lock or constraint violation → unhandled 500.

**Routes to protect** (wrap commit in try/except IntegrityError/OperationalError):

| Route | File:Line |
|---|---|
| `newsletter_reset()` | `admin.py:276` |
| `delete_subscriber()` | `admin.py:673` |
| `rename_tag()` | `admin.py:864` |
| `delete_tag()` | `admin.py:879` |
| `create_tag()` | `admin.py:904` |
| `create_user()` | `admin.py:1055` |
| `delete_user()` | `admin.py:1076` |
| `change_password()` | `admin.py:1093` |
| `revoke_session()` | `admin.py:1129` |
| `logout()` | `admin.py:293` |
| `bulk_operations()` (publish) | `admin.py:988` |
| `bulk_operations()` (unpublish) | `admin.py:996` |
| `bulk_operations()` (delete) | `admin.py:1007` |

Public routes: page view tracking (`public.py:98`) and share tracking (`public.py:281`) should also wrap commits.

#### 2A.2 Log exceptions in the 500 error handler

**File:** `app/__init__.py:98-101`
**Problem:** Handler rolls back session but never logs the exception. Errors only appear in WSGI server logs.
**Fix:** Add `logger.exception("Unhandled exception on %s", request.path)` before returning 500 response.

#### 2A.3 Add logging for admin actions

Use `logger.info` with relevant IDs/names for: post deleted (`admin.py:546`), tag created/renamed/deleted (`admin.py:904/864/879`), user created/deleted (`admin.py:1055/1076`), password changed (`admin.py:1093`), subscriber deleted (`admin.py:673`), session revoked (`admin.py:1129`), unsubscribe (`public.py:399-401`).

### Sub-Agent B: JS Fixes & Improvements

#### 2B.1 Replace inline navbar padding with CSS class toggle

**Files:** `app/static/js/main.js:40-41`, `app/static/css/style.css:127-136`
**Problem:** Scroll handler sets `navbar.style.padding` directly, bypassing CSS transitions.
**Fix:**
1. Add `transition: padding 0.2s ease;` to `.navbar` (prefers-reduced-motion already overrides)
2. Add `.navbar-shrunk { padding: 10px 0; }` class
3. Replace `navbar.style.padding = ...` with `navbar.classList.toggle('navbar-shrunk', window.scrollY > 60)`

#### 2B.2 Scope editor keyboard shortcuts to editor pages

**File:** `app/static/js/main.js:462-490`
**Problem:** `e.preventDefault()` fires before checking if target elements exist. Ctrl+S overrides browser Save on all pages.
**Fix:** Move `querySelector` before `preventDefault` — only prevent when target exists.

#### 2B.3 Increase lazy loading viewport threshold

**File:** `app/static/js/main.js:246`
**Change:** `1.5 * window.innerHeight` → `3 * window.innerHeight`. Current threshold lazy-loads images too close to viewport.

---

## Wave 3 — Code Quality & Testing (parallelizable)

Two independent sub-agents.

### Sub-Agent A: Code Quality

#### 3A.1 Move FTS search logic into `app/search.py`

**File:** `app/routes/public.py:212-230`
**Problem:** `_fts_search()` is in public.py while all other FTS operations are in `app/search.py`.
**Fix:** Add `search(query: str) -> list[int]` to `app/search.py`. Update public.py to import it. Remove local `_fts_search()`.

#### 3A.2 First user promotion is non-deterministic

**File:** `app/__init__.py:223`
**Problem:** `db.select(User)` fetches arbitrary user (no ORDER BY). Comment says "Promote first user to admin."
**Fix:** Add `.order_by(User.id)`.

#### 3A.3 Move `import secrets` to module level

**File:** `app/routes/admin.py:242`
**Problem:** `import secrets` is inside `login()` function body. Module-level imports are the convention.
**Fix:** Move to top of admin.py with other imports.

#### 3A.4 Extract nested `categorize_referrer()` to module level

**File:** `app/routes/admin.py:124-132`
**Problem:** Defined inside `_get_analytics_data()`, recreated on every call. No closure dependencies.
**Fix:** Move to module level as private function.

#### 3A.5 Improve password complexity requirements

**File:** `app/routes/admin.py:1043, 1089`
**Problem:** Only checks `len(password) < 8`. No complexity rules.
**Fix:** Require at least 3 of 4 character classes (lowercase, uppercase, digit, special). Keep 8-char minimum.

#### 3A.6 Simplify config validation flow

**File:** `app/config.py:122-132`
**Problem:** base_url validation appears after first raise, making it look like dead code (fixed in 1A.6 but structure still confusing).
**Fix:** Ensure all validations run before any `raise`. Single raise point at the end.

#### 3A.7 Add type hints to route handlers and utility modules

**Scope:** Route handlers in `admin.py`, `public.py`, `rss.py`, and utility modules `email.py`, `scheduler.py`.
**Approach:** Add return type annotations (`-> Response` for routes, `-> None` for side-effect functions).

### Sub-Agent B: Test Coverage

#### 3B.1 Test `subscribers_bulk` route

**Tests:** Bulk delete, bulk export, empty selection, invalid action.

#### 3B.2 Test admin session management

**Tests:** Session list returns 200, revoke deletes session, revoked session causes login redirect.

#### 3B.3 Test post scheduling

**Tests:** Future-scheduled post stays draft, `publish_scheduled_posts()` publishes past-due posts, clears `scheduled_publish_at`.

#### 3B.4 Test resubscribe flows

**Tests:** Unsubscribed user re-subscribes (clears `unsubscribed_at`), unconfirmed re-subscribes (new token), expired unconfirmed re-subscribes (deletes old, creates new).

#### 3B.5 Test CSV export correctness

**Tests:** Comma in email → properly quoted, double quote → properly escaped, formula injection chars prefixed.

#### 3B.6 Test compressed backup restore

**Tests:** Create `.db.gz` backup, restore it, verify DB functional. Verify `.db` still works.

#### 3B.7 Test analytics data correctness

**Tests:** Page view counts, share event referrer categorization, top posts ranking.

---

## Wave 4 — Accessibility & Content (parallelizable)

Two independent sub-agents.

### Sub-Agent A: Accessibility

#### 4A.1 Add `aria-current` to active nav links

**Files:** `app/templates/base.html`, `app/static/css/style.css`
Apply `aria-current="page"` and `.active` class to matching nav link.

#### 4A.2 Improve focus indicators

**File:** `app/static/css/style.css`
Add stronger `:focus-visible` outlines (2px solid accent, 2px offset). Special handling for form inputs.

#### 4A.3 Add screen reader announcements

**Files:** `app/static/js/main.js`, templates
Add `aria-live="polite"` region. Announce: search result count, bulk operation completion, autosave status.

#### 4A.4 Enhance keyboard navigation

**File:** `app/static/js/main.js`
Add `g` then `d/p/s/t` vim-style navigation (Dashboard, Posts, Subscribers, Tags). 500ms timeout between keys.

#### 4A.5 Widen navbar search input

**File:** `app/static/css/style.css:~1977-1985`
Change default from 150px→200px, focus from 200px→260px.

#### 4A.6 Visible focus for share buttons

**File:** `app/static/css/style.css`
Add `.share-btn:focus-visible` outline rule.

#### 4A.7 Improve form labels and hints

**Files:** `app/templates/admin/editor.html`, `app/templates/admin/subscribers.html`
Add `aria-describedby` hints, proper `<label>` associations.

#### 4A.8 Increase touch target sizes (44x44px WCAG)

**File:** `app/static/css/style.css`
Set `min-height`/`min-width: 44px` on `.btn`, `.nav-links a`, `.tag`, `.share-btn`.

### Sub-Agent B: Content Enhancements

#### 4B.1 Add table of contents for long articles

**Files:** `app/templates/post.html`, `app/static/css/style.css`, `app/static/js/main.js`
Sticky TOC sidebar from `.prose h2/h3`. IntersectionObserver highlights current section. Collapsible on mobile.

#### 4B.2 Add "Last Updated" indicator

**File:** `app/templates/post.html`
Show "Updated: {date}" when `post.updated_at > post.created_at`.

#### 4B.3 Add image lightbox

**Files:** `app/static/css/style.css`, `app/static/js/main.js`
CSS + minimal JS lightbox for `.prose img`. Click opens full-size overlay. Escape/click-outside to close.

#### 4B.4 Add breadcrumb navigation

**Files:** `app/templates/post.html`, `app/templates/tag.html`, `app/static/css/style.css`
Home > Tag > Post Title trail.

#### 4B.5 Improve editor preview loading state

**Files:** `app/static/css/style.css`, `app/static/js/main.js`
Add spinner/skeleton + "Rendering preview…" text during loading.

#### 4B.6 Add visual feedback for share buttons

**Files:** `app/static/css/style.css`, `app/static/js/main.js`
Brief `:active` scale transform. Color flash before opening link.

#### 4B.7 Smooth theme transition

**File:** `app/static/css/style.css`
Add `transition: background-color 0.3s ease, color 0.3s ease` scoped to theme changes.

#### 4B.8 Mobile typography improvements

**File:** `app/static/css/style.css`
Prose `line-height: 1.7` on mobile. Larger tap targets for inline links.

---

## Wave 5 — UI Polish, Admin UX & Perf (parallelizable)

Three independent sub-agents.

### Sub-Agent A: Visual Polish

#### 5A.1 Refine dark mode colors for WCAG contrast

**File:** `app/static/css/style.css`
Verify and adjust contrast ratios (4.5:1 minimum for text).

#### 5A.2 Add subtle CSS animations

**File:** `app/static/css/style.css`
Card hover lift (`translateY(-4px)`), button press (`scale(0.98)`), tag hover highlight. Respect `prefers-reduced-motion`.

#### 5A.3 Image loading states

**Files:** `app/static/css/style.css`, `app/static/js/main.js`
Skeleton placeholder for lazy images. Opacity transition on load.

#### 5A.4 Consistent spacing system

**File:** `app/static/css/style.css`
Define `--space-xs/sm/md/lg/xl/2xl/3xl` variables. Replace hardcoded values where consistent.

#### 5A.5 Unified button styles

**File:** `app/static/css/style.css`
Ensure all buttons use `display: inline-flex`, consistent gap/padding/radius via variables.

#### 5A.6 Print stylesheet

**File:** `app/static/css/style.css`
`@media print`: hide navbar, sidebar, share bar, footer. Force light colors, readable code blocks.

#### 5A.7 Enhance footer

**Files:** `app/templates/base.html`, `app/static/css/style.css`
Add recent posts (3), tag cloud, subscribe form, copyright year range.

#### 5A.8 Copy-permalink toast for heading anchors

**File:** `app/static/js/main.js`
Clicking anchor copies full URL to clipboard. Show "Link copied!" toast.

### Sub-Agent B: Admin UX

#### 5B.1 Add loading states to admin forms

**Files:** admin templates, `app/static/js/main.js`
Disable submit button on click, show "Saving..." text.

#### 5B.2 Better bulk operation feedback

**Files:** `app/templates/admin/dashboard.html`, `app/static/js/main.js`
Progress bar during bulk operations.

#### 5B.3 Improve empty states

**Files:** admin templates, `app/static/css/style.css`
Contextual empty states with helpful actions per page (subscribers, media, sessions).

#### 5B.4 Add dashboard visual hierarchy

**File:** `app/static/css/style.css`
Left-border accent colors on stat cards (views=blue, posts=green, shares=purple, subscribers=orange).

#### 5B.5 Better error pages

**Files:** `app/templates/404.html`, `app/templates/500.html`
Add search box, suggest recent posts, add "Report issue" link.

#### 5B.6 Improve admin navigation

**Files:** `app/templates/admin/base.html`, `app/static/css/style.css`
Active state highlighting, group related items, better mobile responsiveness.

### Sub-Agent C: Performance

#### 5C.1 Optimize image loading attributes

**Files:** templates
Add `loading="lazy"`, `decoding="async"`, explicit `width`/`height` to all post images.

#### 5C.2 Prefetch likely next pages

**File:** `app/static/js/main.js`
Add `<link rel="prefetch">` on link hover (debounced, once per link).

#### 5C.3 Limit newsletter batch size

**File:** `app/scheduler.py:41-51`
Process subscribers in batches of 500 via `yield_per()` or LIMIT/OFFSET. Defensive for large subscriber counts.

#### 5C.4 Request body size validation for preview

**File:** `app/routes/admin.py` (preview-markdown)
Add 1MB body size check before processing (admin-only endpoint, low priority).

---

## Execution Order

```
Wave 1 ─┬─ Sub-Agent A: Backend bugs (1A.1–1A.7)
         └─ Sub-Agent B: CSS/JS dead code (1B.1–1B.6)
              │
Wave 2 ─┬─ Sub-Agent A: Error handling & logging (2A.1–2A.3)
         └─ Sub-Agent B: JS fixes (2B.1–2B.3)
              │
Wave 3 ─┬─ Sub-Agent A: Code quality (3A.1–3A.7)
         └─ Sub-Agent B: Test coverage (3B.1–3B.7)
              │
Wave 4 ─┬─ Sub-Agent A: Accessibility (4A.1–4A.8)
         └─ Sub-Agent B: Content enhancements (4B.1–4B.8)
              │
Wave 5 ─┬─ Sub-Agent A: Visual polish (5A.1–5A.8)
         ├─ Sub-Agent B: Admin UX (5B.1–5B.6)
         └─ Sub-Agent C: Performance (5C.1–5C.4)
```

**Dependencies:**
- Wave 2 depends on Wave 1 (error handling protects the fixed routes)
- Wave 3 depends on Wave 1 (tests validate fixes; code quality follows bug fixes)
- Wave 4 depends on Wave 1 (CSS changes build on cleanup)
- Wave 5 depends on Waves 2–4 (polish on top of solid foundation)

Within each wave, sub-agents are fully independent and touch different files/domains.

---

## Summary

| Wave | Focus | Items | Priority | Parallelizable |
|------|-------|-------|----------|----------------|
| 1 | Critical bugs & dead code | 13 | High | Yes (2 agents) |
| 2 | Error handling & JS fixes | 6 | High | Yes (2 agents) |
| 3 | Code quality & tests | 14 | Medium | Yes (2 agents) |
| 4 | Accessibility & content | 16 | Medium | Yes (2 agents) |
| 5 | UI polish & perf | 18 | Low-Medium | Yes (3 agents) |

**Total: 67 items**

**Critical bugs:** Subscribe race condition → 500 (1A.2), orphan tags never deleted (1A.4), bulk subscribers route accepts GET (1A.1), backup restore corrupts .db.gz (1A.5), CSV injection risk (1A.3).
