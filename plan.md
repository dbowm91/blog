# Consolidated Improvement Plan

Merged from plan2–plan6. Covers bug fixes, CSS/JS cleanup, security hardening, performance, content features, testing, and documentation. Items already completed (from the original plan.md waves 1–8) are **not** repeated here.

**Excluded by design**: Application-level rate limiting (handled by reverse proxy per AGENTS.md).

---

## Guiding Principles

1. **Follow existing patterns** — SQLAlchemy 2.0 queries, `UTCDateTime`, `@admin_required`, existing security headers
2. **Test everything** — All changes must pass `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`
3. **Document changes** — Update `AGENTS.md` with new patterns and lessons learned
4. **No visual redesigns** — Cleanup and bug fixes only, maintain existing design language

---

## Wave 1: Bug Fixes & CSS Cleanup (PARALLEL — 2 agents)

**Agent A — Python Bug Fixes** (from plan6)  
**Agent B — CSS/Template Cleanup** (from plan4 + plan5)

These touch entirely different file types and can run fully in parallel.

### 1A.1 Remove deprecated `db.session.close_all()` in restore_backup
**File**: `app/routes/admin.py:967`  
**Problem**: `db.session.close_all()` emits `SADeprecationWarning` (deprecated since SQLAlchemy 1.3). The `db.engine.dispose()` on line 968 already handles connection cleanup.  
**Fix**: Remove the `db.session.close_all()` call entirely.

### 1A.2 Escape FTS5 search input to prevent syntax errors
**File**: `app/routes/public.py:197-214`  
**Problem**: Double quotes in search input cause `OperationalError: unterminated string` in FTS5 MATCH queries. Currently falls through to LIKE fallback silently.  
**Fix**: Escape double quotes by doubling them (SQLite FTS5 convention: `"` → `""`):
```python
terms = [w.replace('"', '""') for w in query.split() if w]
fts_query = " OR ".join(f'"{t}"' for t in terms)
```

### 1A.3 Replace `assert` with proper guard in search route
**File**: `app/routes/public.py:157`  
**Problem**: `assert all(isinstance(i, int) for i in post_ids)` is a no-op under `python -O`.  
**Fix**: Replace with `if not ... :` guard that logs a warning and falls through to LIKE fallback.

### 1A.4 Remove noisy localhost warning from config
**File**: `app/config.py:130-132`  
**Problem**: `warnings.warn()` fires on every test run for the default `config.toml` (`base_url = "http://localhost:5000"`).  
**Fix**: Remove the localhost check entirely — it's a valid development default. Move production validation to `_validate_config` if desired.

### 1A.5 Clean up trailing blank lines in config.py
**File**: `app/config.py:137-138`  
**Fix**: Remove extra blank line (keep one per PEP 8).

---

### 1B.1 Remove dead CSS classes
**File**: `app/static/css/style.css`  
**Problem**: Multiple CSS classes defined but never used in any template or JS:
- `.status-badge`, `.status-badge.published`, `.status-badge.draft` (lines 1830-1837) — templates use `.badge-published`/`.badge-draft`
- `.loading-skeleton` + `@keyframes shimmer` (lines 926-932)
- `.btn-loading` + `@keyframes spin` (lines 913-925)
- `.img-loading` (line 1967)
- `img[data-src]`, `img[data-src].img-loaded` (lines 1965-1966) — JS uses native `loading="lazy"`
- `.editor-container`, `.editor-tabs`, `.editor-tabs .tab-btn` (lines 1205-1216) — mobile media query, never used
- `.posts-grid` (line 1219) — mobile media query, never used  
**Fix**: Delete all these rules and their associated keyframes.

### 1B.2 Merge duplicate `.btn-ghost` definition
**File**: `app/static/css/style.css` (lines 849-879)  
**Problem**: Defined at lines 849-853, redefined at lines 878-879.  
**Fix**: Merge into single definition with `background: var(--bg-surface)` added to hover state.

### 1B.3 Merge duplicate `.animate-in` and remove dead `fadeSlideIn`
**File**: `app/static/css/style.css` (lines 1950-1974)  
**Problem**: `.animate-in` defined twice — first with `fadeSlideIn` keyframes (dead), second with `fadeInUp`.  
**Fix**: Remove the first definition and `@keyframes fadeSlideIn`. Keep only `fadeInUp`.

### 1B.4 Remove duplicate `:focus-visible` and `:focus:not(:focus-visible)` rules
**File**: `app/static/css/style.css` (lines 2058, 2075-2078, 2062-2064, 2081-2083)  
**Problem**: Each rule defined twice identically.  
**Fix**: Keep first occurrence of each, remove second block.

### 1B.5 Merge duplicate `.stat-card` definitions
**File**: `app/static/css/style.css` (lines 1397-1435)  
**Problem**: `.stat-card` defined at 1397-1404 and again at 1429-1435 with hover transforms and redefined children.  
**Fix**: Merge into single block — add `transform`/`box-shadow` to hover, combine transitions, keep `.stat-label`/`.stat-value`/`.stat-trend` from second definition.

### 1B.6 Consolidate duplicate CSS variables
**File**: `app/static/css/style.css`  
**Problem**:
- `--bg-primary: #0d1117` (line 73) = `--bg: #0d1117` (line 70). Only used by dead `.loading-skeleton`.
- `--text-secondary: #8b949e` (line 78) = `--text-muted: #8b949e` (line 76). Used by `.empty-state` (line 1884) and dead `.stat-card .stat-label` (line 1433).  
**Fix**: Remove `--bg-primary`. Replace `--text-secondary` with `--text-muted` in `.empty-state`. Remove `--text-secondary`.

### 1B.7 Replace hardcoded colors with CSS variables
**File**: `app/static/css/style.css`  
**Problem**: Form errors use `#dc3545` (lines 1281-1285), noscript warning uses `#fff3cd`/`#856404` (lines 2066-2072).  
**Fix**: Use `var(--red)` / `var(--red-dim)` for form errors. Use `rgba(210, 153, 34, 0.15)` + `var(--yellow)` for noscript (or add `--yellow-dim` to `:root`).

### 1B.8 Consolidate reduced-motion rules
**File**: `app/static/css/style.css` (lines 1975-1981, 2086-2104)  
**Problem**: `prefers-reduced-motion` appears twice — blanket disable and selective disable.  
**Fix**: Remove the first blanket rule (lines 1975-1981). Keep the selective version.

### 1B.9 Fix `-ms-hyphens` typo in prism-okaidia.css
**File**: `app/static/css/prism-okaidia.css:17`  
**Problem**: `-ms-hyphins: none` (typo).  
**Fix**: Correct to `-ms-hyphens: none`.

### 1B.10 Standardize pagination labels across templates
**Files**: `app/templates/admin/subscribers.html`, `app/templates/admin/media.html`  
**Problem**: Index/Dashboard use `← Newer` / `Older →`, Subscribers uses `← Prev` / `Next →`, Media uses `← Previous` / `Next →`.  
**Fix**: Standardize all to `← Newer` / `Older →`.

### 1B.11 Remove unused font files
**Files**: `app/static/fonts/inter-cyrillic.woff2`, `app/static/fonts/jetbrains-mono-cyrillic.woff2`, `app/static/fonts/inter-400-latin-ext.woff2`, `app/static/fonts/jetbrains-mono-400-latin-ext.woff2`  
**Problem**: Exist on disk but never referenced in any `@font-face` rule.  
**Fix**: Delete these files.

### 1B.12 Add noscript warning dark-mode support
**File**: `app/static/css/style.css` (lines 2066-2072)  
**Problem**: Hardcoded light-only colors (`#fff3cd`, `#856404`) — bad contrast in dark mode.  
**Fix**: Add dark-mode override:
```css
:root:not([data-theme="light"]) .noscript-warning {
    background: #3b2e00;
    color: #d4a017;
}
```

### 1B.13 Add focus styles for `.prose` links
**File**: `app/static/css/style.css`  
**Problem**: Prose links have `:hover` but no `:focus-visible` offset.  
**Fix**: Add `.prose a:focus-visible { outline-offset: 2px; }`.

### 1B.14 Add light-mode overrides for Prism token colors
**File**: `app/static/css/prism-okaidia.css`  
**Problem**: Token colors are dark-theme-only (light text on assumed dark bg).  
**Fix**: Add `[data-theme="light"]` overrides with GitHub's light theme palette for darker token colors.

---

## Wave 2: JavaScript & Template Fixes (after Wave 1)

Single agent. Depends on Wave 1 being complete to avoid merge conflicts in the same files.

### 2.1 Simplify clipboard handling — remove `execCommand` fallback + add error feedback
**File**: `app/static/js/main.js`  
**Problem**: 3 clipboard sites use deprecated `execCommand` as fallback. Error handlers show no user feedback.  
**Fix**:
- Remove all `execCommand` fallback branches (lines 99, 146, 156)
- In catch handlers, show "Failed" text on the button with timeout revert
- Share bar copy (line 90-113), code block copy (line 137-160), media copy URL (line 444-450)

### 2.2 Fix theme toggle OS change listener
**File**: `app/static/js/main.js:421-428`  
**Problem**: Condition checks `!stored || stored === 'auto'` but `'auto'` is never stored — only `'light'` or `'dark'`.  
**Fix**: Change condition to `!stored` only.

### 2.3 Move inline `onchange` from dashboard filter select to JS
**File**: `app/templates/admin/dashboard.html:55`  
**Problem**: `onchange="this.form.submit()"` is inline JS, incompatible with stricter CSP.  
**Fix**: Move to `main.js` — add handler for `.filter-select` that auto-submits parent form on change.

### 2.4 Move inline `onchange` from analytics select to JS
**File**: `app/templates/admin/analytics.html:11`  
**Problem**: `onchange="window.location.href=..."` is inline JS.  
**Fix**: Move to `main.js` with `data-auto-submit` attribute pattern.

### 2.5 Guard "Back to editor" link in `_post_content.html`
**File**: `app/templates/_post_content.html:51`  
**Problem**: Admin link visible if partial is ever included on public pages.  
**Fix**: Wrap in `{% if current_user.is_authenticated and current_user.is_admin %}`.

### 2.6 Add label for "Select all" checkbox
**File**: `app/templates/admin/dashboard.html:68`  
**Problem**: Checkbox has only `title="Select all"`, no `<label>` or `aria-label`.  
**Fix**: Add `aria-label="Select all posts"`.

### 2.7 Add `lang="en"` to email templates
**Files**: `app/templates/email/confirm.html`, `app/templates/email/newsletter.html`  
**Problem**: Missing `lang` attribute on `<html>` tags.  
**Fix**: Add `lang="en"` to both.

---

## Wave 3: Database & Infrastructure (after Wave 1)

Single agent. No overlap with Wave 1 file changes.

### 3.1 Remove unnecessary SQLite pool settings
**File**: `app/__init__.py:57-60`  
**Problem**: `pool_pre_ping` and `pool_recycle` add overhead without value for SQLite (local file, no network connections).  
**Fix**: Remove `SQLALCHEMY_ENGINE_OPTIONS` block entirely.

### 3.2 Enable SQLite WAL mode
**File**: `app/__init__.py` (after database URI configuration)  
**Problem**: Default rollback journal mode blocks concurrent readers during writes.  
**Fix**: Enable WAL on startup:
```python
with app.app_context():
    db.session.execute(text("PRAGMA journal_mode=WAL"))
    db.session.commit()
```
Add `PRAGMA busy_timeout=5000` for write contention.

### 3.3 Remove redundant Subscriber index definitions
**File**: `app/models.py` (Subscriber `__table_args__`)  
**Problem**: Explicit indexes on `token` and `email` duplicate the automatic indexes from `unique=True`.  
**Fix**: Remove redundant indexes, keep only the composite index `ix_subscribers_confirmed_unsubscribed`.

### 3.4 Add FTS5 rebuild CLI command
**File**: `app/__init__.py` (CLI commands section)  
**Problem**: No way to rebuild the FTS index from CLI without restarting the app.  
**Fix**: Add `flask rebuild-search` CLI command that calls `rebuild_fts()`.

### 3.5 Improve FTS5 error logging with context
**File**: `app/search.py`  
**Problem**: FTS5 failures don't include which posts are affected.  
**Fix**: Add post IDs and operation type to warning messages.

---

## Wave 4: Security Hardening (after Wave 1)

Single agent. Independent of other waves.

### 4.1 Add `X-Download-Options` header
**File**: `app/__init__.py` (set_security_headers)  
**Fix**: Add `response.headers["X-Download-Options"] = "noopen"` — prevents IE from executing downloads in site context.

### 4.2 Add `X-Permitted-Cross-Domain-Policies` header
**File**: `app/__init__.py` (set_security_headers)  
**Fix**: Add `response.headers["X-Permitted-Cross-Domain-Policies"] = "none"` — prevents Flash/PDF cross-domain policy files.

### 4.3 Validate upload file size before processing
**File**: `app/routes/admin.py` (`_save_image`)  
**Problem**: No size check before magic byte detection — large files could cause memory issues.  
**Fix**: Check file size before processing (e.g., 10MB limit for images).

### 4.4 Document session timeout mechanism
**File**: `app/__init__.py` (cookie config section)  
**Problem**: Custom `last_activity` sliding expiration isn't documented; future devs might add conflicting `PERMANENT_SESSION_LIFETIME`.  
**Fix**: Add comment explaining the custom mechanism.

### 4.5 Tighten Content Security Policy with nonces
**File**: `app/__init__.py`, `app/templates/base.html`  
**Problem**: `style-src 'unsafe-inline'` weakens CSP.  
**Fix**: Generate per-request nonce, replace `'unsafe-inline'` with nonce-based approach. Add CSP `report-uri` for violation logging.  
**Note**: This is high-effort — all inline styles must use the nonce. Consider deferring if current CSP is acceptable.

### 4.6 Admin session security enhancements
**Files**: `app/__init__.py`, `app/routes/admin.py`, `app/models.py`  
**Features**: Session fingerprinting (User-Agent + IP hash), session activity log, "Sessions" admin page, "Revoke all other sessions" button.  
**Note**: Significant scope — include `Session` model + migration.

---

## Wave 5: Performance & Content Features (after Wave 3)

**Agent A — Performance**  
**Agent B — Content Features**

Parallel — different concerns, though both touch `app/routes/admin.py`.

### 5A.1 Extract common post query utility
**File**: `app/routes/admin.py`  
**Problem**: Multiple routes repeat the pattern of fetching posts with `joinedload` and pagination.  
**Fix**: Create `_get_posts_query(status, search)` utility function.

### 5A.2 Add query result caching for analytics
**File**: `app/routes/admin.py` (analytics route)  
**Problem**: Expensive aggregation queries run on every request.  
**Fix**: Simple in-memory caching with TTL (default 300s).

### 5A.3 Stream subscriber CSV export
**File**: `app/routes/admin.py` (export route)  
**Problem**: Loads all subscribers into memory at once.  
**Fix**: Use generator + `Response(mimetype="text/csv")` for streaming.

### 5A.4 Add composite database indexes for common queries
**File**: `app/models.py`  
**Problem**: Dashboard and subscriber queries may be slow at scale.  
**Fix**: Add composite indexes based on query patterns. Requires migration.

### 5A.5 Static asset content hashing
**File**: `app/__init__.py`, `app/templates/base.html`  
**Problem**: No cache busting for updated CSS/JS files.  
**Fix**: Add content hash to static filenames for cache busting.

### 5B.1 Add post scheduling
**Files**: `app/models.py`, `app/routes/admin.py`, `app/scheduler.py`, `app/templates/admin/editor.html`  
**Features**: `scheduled_at` column on Post, scheduler job to auto-publish, date/time picker in editor, dashboard filter.  
**Requires**: New migration.

### 5B.2 Add batch operations for subscribers
**Files**: `app/routes/admin.py`, `app/templates/admin/subscribers.html`  
**Features**: Checkboxes on subscriber rows, bulk delete, bulk export selected, confirmation dialogs.

### 5B.3 Improve mobile responsiveness for admin
**Files**: `app/static/css/style.css`, `app/templates/`  
**Focus**: Dashboard tables (horizontal scroll or card layout), editor split-pane (stack on mobile), media gallery grid.

---

## Wave 6: Testing, UX & Observability (after Wave 5)

**Agent A — Testing & Observability**  
**Agent B — UX Polish**

### 6A.1 Add integration tests for critical paths
**File**: `tests/`  
**Coverage**: Full post creation workflow, newsletter subscription flow, backup/restore cycle.

### 6A.2 Add test for FTS5 search with special characters
**File**: `tests/test_public.py`  
**Coverage**: Search input containing `"`, `*`, `:`, `-` — verify no 500 error.

### 6A.3 Add test for backup restore deprecation-free
**File**: `tests/test_phase8.py`  
**Coverage**: Verify no `DeprecationWarning` emitted from restore path.

### 6A.4 Improve health check endpoint
**File**: `app/routes/public.py:396-411`  
**Additions**: Disk space check, FTS index health, scheduler job status with last run times, memory usage.

### 6A.5 Enhance logging with request context
**File**: `app/__init__.py` (configure_logging)  
**Addition**: Request context filter adding IP to log records for production debugging.

### 6B.1 Add keyboard shortcuts for admin
**File**: `app/static/js/main.js`  
**Shortcuts**: `Ctrl+S` save draft, `Ctrl+Enter` publish, `Escape` close modals, `?` show help.

### 6B.2 Improve test fixture organization
**File**: `tests/conftest.py`  
**Problem**: `_db.create_all()` called in both session-scoped `app` fixture and function-scoped `db` fixture.  
**Fix**: Remove redundant call from `app` fixture, keep only in `db` fixture.

---

## Wave 7: Documentation & Type Safety (after Wave 6)

Can run fully in parallel with multiple agents.

### 7.1 Add type hints to route functions
**Files**: All route files  
**Fix**: Add `ResponseReturnValue` return types and parameter type hints.

### 7.2 Add API documentation (docstrings)
**Files**: `app/routes/public.py`, `app/routes/admin.py`  
**Focus**: JSON endpoints (`/api/track-share`, `/admin/preview-markdown`) — request/response format docstrings.

### 7.3 Add deployment guide
**File**: New `docs/deployment.md` or update `README.md`  
**Content**: Reverse proxy config (nginx/Caddy), HTTPS setup, env vars, backup strategy, monitoring, scaling.

### 7.4 Update AGENTS.md with new patterns
Document all new patterns and lessons learned from this plan's implementation.

---

## Wave 8: Advanced Features (Backlog)

Lower priority — implement as needed. Each is independent.

### 8.1 Webhook support
`Webhook` model (url, events, secret), dispatch on events (post_published, new_subscriber), HMAC verification, retry with backoff, management UI.

### 8.2 Multi-language support
`language` column on Post (ISO 639-1), language filter in search/tags, `<link rel="alternate" hreflang>` tags, language selector in editor.

### 8.3 Content analytics API
`/api/v1/analytics/posts` and `/api/v1/analytics/subscribers` endpoints with date range filtering and API key auth.

### 8.4 API key authentication
`ApiKey` model (key_hash, name, scopes), generation UI, scope-based access control (posts:read, posts:write, analytics:read).

### 8.5 Post revisions
`PostRevision` model (post_id, title, body, summary, edited_at), revision on each edit, history UI, "Restore this revision" functionality, configurable limit (default 20).

### 8.6 Table of contents generation
Auto-detect headings in markdown, generate TOC with anchor links, `[TOC]` directive support, collapsible sections.

---

## Quick Wins (Single Session)

Items that can be implemented quickly with minimal risk:

1. **1A.1** Remove deprecated `close_all()` — 1 line deletion
2. **1A.4** Remove localhost warning — delete 3 lines
3. **3.1** Remove SQLite pool settings — delete 4 lines
4. **3.2** Enable WAL mode — 3 lines of code, significant concurrent read improvement
5. **1B.9** Fix `-ms-hyphens` typo — 1 character change
6. **1A.3** Replace assert with guard — 3 line rewrite

---

## Migration Notes

Database changes requiring migrations:
- **3.3** Subscriber index cleanup
- **5A.4** Composite indexes
- **5B.1** `scheduled_at` column on Post
- **4.6** Session model (if implemented)
- **8.1** Webhook model
- **8.2** Language column
- **8.4** ApiKey model
- **8.5** PostRevision model

All migrations should include:
1. Migration script in `migrations/versions/`
2. Data migration for existing records (if needed)
3. Rollback plan documented in migration docstring

---

## Testing

After each wave:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Review Checklist

Before marking any wave complete:
- [ ] All tests pass (no regression from 189 baseline)
- [ ] No new security vulnerabilities introduced
- [ ] No visual regressions (verify dark/light mode, mobile layout)
- [ ] `AGENTS.md` updated with new patterns
- [ ] Rollback plan documented for database changes
