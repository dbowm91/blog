# Implementation Plan - Blog CMS

**Project:** Blog CMS
**Status:** ACTIVE - Maintenance mode
**Last Updated:** May 2026

---

## Overview

This file contains the current implementation plan for the Blog CMS project. All waves A-I have been completed. This file now serves as a reference for important implementation details.

---

## Completed Implementation Waves

| Wave | Description | Items | Status |
|------|-------------|-------|--------|
| A | 2FA Security (TOTP + Backup Codes) | 2 | COMPLETED |
| B | Rate Limiting Infrastructure | 1 | COMPLETED |
| C | Search Infrastructure (PostgreSQL) | 1 | COMPLETED |
| D | Frontend Enhancements (Vite + AVIF) | 2 | COMPLETED |
| E | Performance (Brotli) | 1 | COMPLETED |
| F | Bug Fixes (Security & Functional) | 12 | COMPLETED |
| G | Code Quality | 5 | COMPLETED |
| H | Documentation | 37 | COMPLETED |
| I | Enhancements | 0 | N/A |

**Total: 61 items completed**

---

## Current Focus

The project is in **maintenance mode**. No active implementation waves are in progress.

For future enhancement ideas, see the `plans/` directory or create a new wave proposal.

---

## Key Implementation Details (Reference)

### 2FA Implementation (Wave A)
- TOTP secrets are encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is now a property that decrypts on access
- Backup codes are SHA-256 hashed and single-use
- Routes: `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable`

### Rate Limiting (Wave B)
- `ADMIN_RATE_LIMITS` defined in `app/config.py`
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class

### Search Abstraction (Wave C)
- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` wraps existing FTS5 functionality
- `PostgreSQLSearchProvider` is a stub for future implementation

### Frontend (Wave D)
- Vite configured for code splitting with `manualChunks`
- `post_image_avif_url_stub` filter (returns None until AVIF encoding is properly implemented)

### Brotli (Wave E)
- Nginx configuration includes commented Brotli settings
- Requires custom nginx image with `--with-http_brotli_module`

### Backup Naming (Wave F - F.2)
Both backup implementations now use `blog_*.db` naming:
- `app/services/backup.py:create_backup()` - Used by Celery task, supports encryption/compression
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression

### Preview Route Security (Wave F - F.1)
The public preview route at `/preview/<int:post_id>` requires both HMAC token validation AND admin session verification (`session.get('admin_user_id')`).

### Shared Test Fixtures (Wave F - F.7)
The `ensure_buffer_disabled` fixture is consolidated in `tests/shared_fixtures.py`.

### Deprecations (Wave G)
- `deliver_webhook()` in `app/webhooks.py` is deprecated - use `deliver_webhook_task` Celery task instead

---

## Wave Execution Pattern (Reference)

When executing multi-wave implementation plans:
1. **Create separate branches** for each parallel wave to avoid conflicts
2. **Use subagents** with separate branches to parallelize work
3. **Merge to main** after each wave completes
4. **Update plan status** in plan.md after each wave

### Branch Naming Convention
```
wave-f-bugfixes
wave-g-code-quality
wave-h-documentation
wave-i-enhancements
```

---

## Important Notes for Future Agents

### Security
- **Log ID, not Username**: When logging user actions, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

### Configuration
- Configuration priority: env vars > config.toml > defaults
- Newsletter retry count default is 5

### APScheduler Job Schedules
- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

### Slug Generation
- Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`)

### Celery Queue Names
- Tasks use specific queues: `images`, `newsletter`, `webhooks`, `email`, `backup`

### Routes (Verify Before Using)
When documenting or referring to routes, verify against actual implementation:
- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)

### Template Filters (Actual)
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Context Processors (Actual Function Names)
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

---

## High-Risk Files (Error Handling - Fixed)

These files previously had exception handling issues but are now fixed:

| File | Issue | Status |
|------|-------|--------|
| `app/routes/public/meta.py` | Broad exception | FIXED |
| `app/email.py` | SMTP exception too broad | FIXED - Wave G |
| `app/backup_integrity.py` | Previously broad exception | FIXED |
| `app/webhooks.py` | Silent failure with `pass` | FIXED - Wave F |
| `app/tasks.py` | Broad `except Exception` | FIXED - Wave F |
| `app/page_view_buffer.py` | Previously broad exception | FIXED |

---

## Test Interference Notes

### Page View Buffer
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `ensure_buffer_disabled` fixture is in `tests/shared_fixtures.py`

### Test Database Session
- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`

---

## Creating New Implementation Waves

To propose a new enhancement or bug fix:
1. Create a branch: `wave-<letter>-<description>`
2. Implement the changes following existing patterns
3. Update this file with the new wave information
4. Create a PR for review

---

*Last updated: May 2026 - All Waves A-I completed*