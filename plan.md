# Consolidated Improvement Plan

Generated from codebase review on 2026-04-01. All items verified against current code.
Supersedes plan2.md, plan3.md, plan4.md, plan5.md, plan6.md.

**Status: All waves complete. All 228 tests pass.**

Each wave builds on the previous. Sub-agents within a wave can run in parallel since they touch different files/domains.

---

## Wave 1 — Critical Bugs & Dead Code ✅

Two independent sub-agents: **Backend** and **CSS/JS**.

### Sub-Agent A: Backend Bugs

#### 1A.1 Fix `subscribers_bulk` route accepting GET ✅

**File:** `app/routes/admin.py`
**Problem:** Route decorator defaults to GET-only but reads `request.form`, which is empty on GET.
**Fix:** Added `methods=["POST"]` to the route decorator.

#### 1A.2 Fix subscribe race condition (IntegrityError) ✅

**File:** `app/routes/public.py`
**Problem:** Two concurrent subscribe requests with the same email both pass check, then both try to insert → unhandled IntegrityError.
**Fix:** Wrapped insert + commit in `try/except IntegrityError`. On collision, re-queries existing subscriber.

#### 1A.3 Fix CSV export field escaping ✅

**Files:** `app/routes/admin.py`
**Problem:** CSV built with f-strings. Commas, quotes, or newlines in emails break CSV formatting.
**Fix:** Used `csv.writer` via `io.StringIO`. Cells starting with `=`, `+`, `-`, `@` prefixed with `'` to prevent CSV formula injection.

#### 1A.4 Fix orphan tag cleanup never persisting ✅

**Files:** `app/routes/admin.py`
**Problem:** `_cleanup_orphan_tags()` was called *after* `db.session.commit()` in all three callers.
**Fix:** Moved `_cleanup_orphan_tags()` and `invalidate_tag_cache()` to before `db.session.commit()`.

#### 1A.5 Fix backup restore doesn't decompress .db.gz ✅

**File:** `app/routes/admin.py`
**Problem:** Restore used `shutil.copy2()` directly for .db.gz backups, copying compressed bytes as the database.
**Fix:** Added gzip decompression to temp file before copying for .gz files.

#### 1A.6 Fix base URL validation unreachable ✅

**File:** `app/config.py`
**Problem:** `raise RuntimeError` fired before the base_url check.
**Fix:** Moved base_url validation before the first `if errors: raise`.

#### 1A.7 Remove unused imports ✅

**Files:** `app/routes/admin.py`, `app/routes/public.py`
**Fix:** Removed unused `csv`, `io` from admin.py; removed unused `invalidate_tag_cache` from public.py import.

### Sub-Agent B: CSS/JS Dead Code

#### 1B.1 Fix mobile nav animation class mismatch ✅

**Files:** `app/static/css/style.css`, `app/static/js/main.js`
**Problem:** CSS defined `.nav-links.active` but JS toggles `.open`.
**Fix:** Changed CSS to `.nav-links.open`, gated `::before` backdrop on `.nav-links.open::before`.

#### 1B.2 Remove duplicate prose heading sizes ✅

**Fix:** Removed duplicate `.prose h1/h2/h3` sizes that were overwritten.

#### 1B.3 Remove duplicate `.copy-code-btn` in style.css ✅

**Fix:** Removed duplicate definition (prism-okaidia.css has the complete version).

#### 1B.4 Remove duplicate mobile `.post-card-body` padding ✅

**Fix:** Removed duplicate padding definition.

#### 1B.5 Remove deprecated vendor prefixes ✅

**File:** `app/static/css/prism-okaidia.css`
**Fix:** Removed `-webkit-hyphens`, `-moz-hyphens`, `-ms-hyphens`.

#### 1B.6 Remove orphan mobile editor CSS ✅

**Fix:** Removed CSS referencing non-existent classes.

---

## Wave 2 — Error Handling, Logging & JS Fixes ✅

Two independent sub-agents.

### Sub-Agent A: Error Handling & Logging

#### 2A.1 Add error handling to unguarded `db.session.commit()` calls ✅

Multiple admin routes wrapped with `try/except IntegrityError/OperationalError`:
- `newsletter_reset()`, `logout()`, `delete_subscriber()`, `rename_tag()`, `delete_tag()`, `create_tag()`
- `bulk_operations()` publish/unpublish/delete branches
- `create_user()`, `delete_user()`, `change_password()`, `revoke_session()`
- Public routes: page view tracking, share tracking

#### 2A.2 Log exceptions in the 500 error handler ✅

**File:** `app/__init__.py`
**Fix:** Added `app.logger.exception("Unhandled exception on %s", req.path)` before returning 500 response.

#### 2A.3 Add logging for admin actions ✅

Added `logger.info()` calls for: post deleted, tag created/renamed/deleted, user created/deleted, password changed, subscriber deleted, session revoked, unsubscribe.

### Sub-Agent B: JS Fixes & Improvements

#### 2B.1 Replace inline navbar padding with CSS class toggle ✅

**Fix:** Added `.navbar-shrunk { padding: 10px 0; }` class with `transition: padding 0.2s ease`, replaced inline style with `classList.toggle('navbar-shrunk', ...)`.

#### 2B.2 Scope editor keyboard shortcuts to editor pages ✅

**Fix:** Moved `e.preventDefault()` inside each `if (target)` block for Ctrl+S, Ctrl+Enter, Ctrl+Shift+P.

#### 2B.3 Increase lazy loading viewport threshold ✅

**Fix:** Changed from `1.5 * window.innerHeight` to `3 * window.innerHeight`.

---

## Wave 3 — Code Quality & Testing ✅

Two independent sub-agents.

### Sub-Agent A: Code Quality

#### 3A.1 Move FTS search logic into `app/search.py` ✅

**Fix:** Added `search(query: str)` to `app/search.py`. Updated `public.py` to import it. Removed local `_fts_search()`.

#### 3A.2 First user promotion is non-deterministic ✅

**Fix:** Added `.order_by(User.id)` to query in `app/__init__.py`.

#### 3A.3 Move `import secrets` to module level ✅

**Fix:** Moved from inside `login()` function body to top of admin.py.

#### 3A.4 Extract nested `categorize_referrer()` to module level ✅

**Fix:** Created `_categorize_referrer(url)` at module level in `admin.py`.

#### 3A.5 Improve password complexity requirements ✅

**Fix:** Added `_check_password_complexity()` requiring at least 3 of 4 character classes (lowercase, uppercase, digit, special). Minimum 8 characters.

#### 3A.6 Simplify config validation flow ✅

**Fix:** Refactored for single raise point at the end.

#### 3A.7 Add type hints to route handlers and utility modules ✅

**Scope:** Added return type annotations to all route handlers and utility functions.

### Sub-Agent B: Test Coverage

#### 3B.1 Test `subscribers_bulk` route ✅

Bulk delete, bulk export, empty selection, invalid action.

#### 3B.2 Test admin session management ✅

Session list returns 200, revoke deletes session, revoked session causes login redirect.

#### 3B.3 Test post scheduling ✅

Future-scheduled post stays draft, `publish_scheduled_posts()` publishes past-due posts, clears `scheduled_publish_at`.

#### 3B.4 Test resubscribe flows ✅

Unsubscribed user re-subscribes, unconfirmed re-subscribes (new token), expired unconfirmed re-subscribes.

#### 3B.5 Test CSV export correctness ✅

Comma in email, double quote, formula injection chars prefixed.

#### 3B.6 Test compressed backup restore ✅

Create .db.gz backup, decompress and verify SQLite validity. Uncompressed backup still works.

#### 3B.7 Test analytics data correctness ✅

Page view counts, share event referrer categorization, top posts ranking.

---

## Wave 4 — Accessibility & Content ✅

Two independent sub-agents.

### Sub-Agent A: Accessibility

#### 4A.1 Add `aria-current` to active nav links ✅

Applied `aria-current="page"` and `.active` class to matching nav links in public and admin templates.

#### 4A.2 Improve focus indicators ✅

Added stronger `:focus-visible` outlines (2px solid accent, 2px offset).

#### 4A.3 Add screen reader announcements ✅

Added `aria-live="polite"` region. Announces: search result count, bulk operation completion, autosave status.

#### 4A.4 Enhance keyboard navigation ✅

Added `g` then `d/p/s/t` vim-style navigation (Dashboard, Posts, Subscribers, Tags). 500ms timeout between keys.

#### 4A.5 Widen navbar search input ✅

Default from 150px→200px, focus from 200px→260px.

#### 4A.6 Visible focus for share buttons ✅

Added `.share-btn:focus-visible` outline rule.

#### 4A.7 Improve form labels and hints ✅

Added `aria-describedby` hints, proper `<label>` associations in editor.

#### 4A.8 Increase touch target sizes (44x44px WCAG) ✅

Set `min-height`/`min-width: 44px` on `.btn`, `.nav-links a`, `.tag`, `.share-btn`.

### Sub-Agent B: Content Enhancements

#### 4B.1 Add table of contents for long articles ✅

Sticky TOC sidebar from `.prose h2/h3`. IntersectionObserver highlights current section.

#### 4B.2 Add "Last Updated" indicator ✅

Shows "Updated: {date}" when `post.updated_at > post.created_at`.

#### 4B.3 Add image lightbox ✅

CSS + JS lightbox for `.prose img`. Click opens full-size overlay. Escape/click-outside to close.

#### 4B.4 Add breadcrumb navigation ✅

Home > Tag > Post Title trail on post and tag pages.

#### 4B.5 Improve editor preview loading state ✅

Added spinner animation with "Rendering preview…" text.

#### 4B.6 Add visual feedback for share buttons ✅

Brief `:active` scale transform. Color flash before opening link.

#### 4B.7 Smooth theme transition ✅

Added `transition: background-color 0.3s ease, color 0.3s ease` to body.

#### 4B.8 Mobile typography improvements ✅

Prose `line-height: 1.7` on mobile. Larger tap targets for inline links.

---

## Wave 5 — UI Polish, Admin UX & Perf ✅

Three independent sub-agents.

### Sub-Agent A: Visual Polish

#### 5A.1 Refine dark mode colors for WCAG contrast ✅

Adjusted `--text-dim` from `#484f58` to `#656d76` for 4.5:1 contrast.

#### 5A.2 Add subtle CSS animations ✅

Extended `prefers-reduced-motion` to disable animations on interactive elements.

#### 5A.3 Image loading states ✅

Added `.img-skeleton` shimmer animation. Lazy images get opacity transition on load.

#### 5A.4 Consistent spacing system ✅

Defined `--space-xs/sm/md/lg/xl/2xl/3xl` variables. Applied to footer, buttons, components.

#### 5A.5 Unified button styles ✅

All buttons use `display: inline-flex` with consistent gap/padding/radius via variables.

#### 5A.6 Print stylesheet ✅

`@media print` hides navbar, sidebar, share bar, footer. Forces light colors.

#### 5A.7 Enhance footer ✅

Three-column grid: Recent Posts, Tags, Subscribe form. Copyright shows year range.

#### 5A.8 Copy-permalink toast for heading anchors ✅

Clicking anchor copies full URL to clipboard. Shows "Link copied!" toast.

### Sub-Agent B: Admin UX

#### 5B.1 Add loading states to admin forms ✅

Disables submit button on click, shows "Saving..." text.

#### 5B.2 Better bulk operation feedback ✅

Progress bar during bulk operations.

#### 5B.3 Improve empty states ✅

Contextual empty states for subscribers, media, sessions pages.

#### 5B.4 Add dashboard visual hierarchy ✅

Left-border accent colors on stat cards (views=blue, posts=green, shares=purple, subscribers=orange).

#### 5B.5 Better error pages ✅

404 and 500 pages now include search box and recent posts.

#### 5B.6 Improve admin navigation ✅

Active state indicators, visual separators for grouping related items.

### Sub-Agent C: Performance

#### 5C.1 Optimize image loading attributes ✅

Added `loading="lazy"`, `decoding="async"`, explicit `width`/`height` to all post images.

#### 5C.2 Prefetch likely next pages ✅

`<link rel="prefetch">` on link hover (debounced 100ms, once per link).

#### 5C.3 Limit newsletter batch size ✅

Uses `yield_per(500)` to stream subscribers in batches.

#### 5C.4 Request body size validation for preview ✅

Added 1MB body size check before processing preview-markdown endpoint.

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

| Wave | Focus | Items | Priority | Status |
|------|-------|-------|----------|--------|
| 1 | Critical bugs & dead code | 13 | High | ✅ Complete |
| 2 | Error handling & JS fixes | 6 | High | ✅ Complete |
| 3 | Code quality & tests | 14 | Medium | ✅ Complete |
| 4 | Accessibility & content | 16 | Medium | ✅ Complete |
| 5 | UI polish & perf | 18 | Low-Medium | ✅ Complete |

**Total: 67 items — All complete. 228 tests passing.**
