---
name: blog_wave_g_h_i
description: "Blog CMS Wave G-I - Lightbox improvements, dashboard widgets, toasts, mobile editor, error pages, structured logging, health check, graceful shutdown, PostgreSQL guide, Docker Compose, property-based tests, E2E tests, benchmarks. Triggers: lightbox keyboard/swipe/zoom, dashboard charts, toast notifications, mobile editor, error pages, JSON logging, health check details, graceful shutdown, PostgreSQL migration, Docker Compose, property-based testing, Playwright E2E, performance benchmarks."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Wave G: UI/UX

### G1: Image Gallery/Lightbox Improvements

`app/static/js/public/lightbox.js` — Complete rewrite:
- **Keyboard navigation**: `←`/`→` arrows to navigate between images
- **Zoom**: Double-click toggles 2x zoom; single click when not zoomed closes
- **Captions**: Alt text displayed at bottom with fade-in
- **Swipe support**: 50px threshold touch swipe

### G2: Better Dashboard Widgets

`app/routes/admin/helpers/dashboard.py`:
- `_get_daily_views(days)` — daily view counts
- `_get_top_posts_by_shares(limit)` — top posts by share count

**New widgets in dashboard**:
- Traffic chart — CSS bar chart, last 30 days
- Top Shares list — top 5 posts by shares

### G3: Toast Notifications

`app/static/js/shared/toast.js`:
- `showToast(message, type)` — type: success, error, warning, info
- Auto-dismiss after 5 seconds
- Stack up to 5 toasts
- Converts existing flash messages to toasts on page load

### G4: Improved Mobile Editor

`app/templates/admin/editor.html`:
- `.editor-textarea-wrapper` with toggle preview button
- Preview hidden by default on mobile
- Taller textarea on mobile (`min-height: 300px`)
- Better datetime-local input styling (`min-height: 44px`)

### G5: Better Error Pages

`app/templates/_error.html`:
- Search box on 404 pages
- Friendly apology on 500 pages
- Primary button for "Back to home"
- History back button

## Wave H: Production Operations

### H1: Structured Logging

`app/__init__.py`:
- `StructuredLogFormatter` — JSON output
- Fields: `timestamp`, `level`, `request_id`, `message`, `exception`

Example:
```json
{"timestamp": "2026-04-21T14:30:00Z", "level": "INFO", "request_id": "a1b2c3d4", "message": "Post published"}
```

### H2: Health Check Enhancement

`app/routes/public.py` `/health`:
- Basic: `status`, `checks`, `timestamp`
- Detailed (`?detailed=true&secret=<secret>`): `database_latency_ms`, `scheduler_next_run`, `scheduler_last_newsletter_send`

**Health check secret**: `HEALTH_CHECK_SECRET` env var

### H3: Graceful Shutdown

`run.py`:
- `signal.signal(signal.SIGTERM, _shutdown_handler)`
- Sets shutdown event, waits for in-flight requests
- `scheduler.shutdown(wait=True)` — finish current newsletter
- `db.engine.dispose()` — close DB connections

### H4: PostgreSQL Migration Guide

`DEPLOY.md`:
- Prerequisites (PostgreSQL 13+, pg_trgm extension)
- Step-by-step migration commands
- FTS5 → `tsvector` migration
- Known limitations table

### H5: Docker Compose Production Profile

**Files**:
- `docker-compose.yml` — production stack
- `Dockerfile` — gunicorn-based image
- `nginx/nginx.conf` — gzip, static caching
- `nginx/conf.d/blog.conf` — upstream proxy

**Services**:
- `blog` — Flask + gunicorn (2 workers)
- `nginx` — reverse proxy
- `backup` — on-demand backup automation

**Usage**:
```bash
docker-compose --profile production up -d
```

## Wave I: Testing Infrastructure

### I1: Property-Based Testing

`tests/test_property_based.py`:
- 139 parametrized test cases
- Slug generation edge cases
- Email validation boundaries
- Password complexity enforcement
- CSS sanitization

### I2: End-to-End Browser Tests

`tests/e2e/`:
- Playwright-based browser tests
- `TestAdminLogin` — login/logout
- `TestPostCreation` — post editor
- `TestNewsletterSubscription` — subscribe flow
- `TestMobileResponsiveness` — mobile nav

**Requires**: `playwright` in requirements.txt

### I3: Performance Benchmarks

`tests/benchmarks/`:
- Search performance (FTS, LIKE fallback)
- Dashboard load time
- Query counts
- Newsletter batch timing
- FTS indexing performance
- Tag caching performance

**Run**: `pytest tests/benchmarks/ --benchmark-only`

## Tests

```bash
cd /home/sugarwookie/projects/blog && source .venv/bin/activate
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```