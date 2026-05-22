# Architecture Review Skill

## Description
Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans.

## Triggers
architecture, review, documentation, verify, cross-reference

## Module Directories
- `architecture/core/` - app-factory.md, configuration.md, models.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, backup.md, serialization.md, slug.md, tag.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md
- `architecture/deployment/` - overview.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

## Output
Each module review writes to `architecture/plans/<module>_review.md`:
- Verified Accurate Claims
- Inaccurate/Outdated Claims (with corrections)
- Missing Documentation
- Potential Issues
- Recommended Improvements

## Review Methodology
1. Read all architecture documents in module directory
2. Cross-reference claims against actual source code
3. Verify route paths, function signatures, configuration values
4. Check AGENTS.md for pre-verified actual behavior
5. Identify discrepancies, outdated info, missing docs
6. Note potential bugs or security issues
7. Write structured improvement plan

## Key Verification Points

### Routes
- `/admin/new` (NOT `/admin/posts/new`)
- `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- `POST /subscribe` only (no GET handler)
- `PUT /api/posts/<id>` with `{"published": true}` (NOT `POST /api/posts/<id>/publish`)

### Configuration
- Newsletter retry count: 5 (not 3)
- APScheduler: cleanup_expired_subscribers every 5 min, run_daily_backup at 02:00
- Celery queues: images (31), newsletter (130), webhooks (182), email (262, 283), backup (304)

### Models
- User.totp_secret is encrypted property (not column)
- User.__repr__ returns `<User id={self.id}>` (PII protection)
- Comment uses back_populates for parent/replies

### Security
- CSP nonce used in headers
- LOGIN_FAILURE_DELAY only in auth.py handlers
- Page view buffer can cause test interference

## Status

### Wave N Completed (May 2026)
All Wave N implementation items verified and completed. Plan pruned to summary status.

| Priority | Fix | Location |
|----------|-----|----------|
| High | Email task retry logic (N-1.1) | `app/tasks.py:264,285` - added `max_retries=3` and `self.retry(exc=e)` |
| High | mobile-menu.jsx import (N-1.2) | `app/static/js/main.js:18,72` - corrected .js → .jsx |
| Medium | 11 documentation fixes (N-2.1-N-2.11) | ADMIN_RATE_LIMITS, S3 env vars, Webhook encryption, delivery_status, Search config/indexing, routes docs, Docker v2, Permissions-Policy, Python version |
| Low | 10 improvements (N-3.1-N-3.10) | email.md, serialization, slug, benchmark fixtures, FTS cleanup, stale line numbers, deprecation notice, backup naming, AGENTS.override.md |

**Verification Notes:**
- Email tasks now properly retry on failure with `max_retries=3` and `self.retry(exc=e)` with exponential backoff.
- mobile-menu file is `mobile-menu.jsx` (JSX syntax), Vite glob matched it despite wrong extension in import.
- Permissions-Policy header documented but never implemented in nginx or Flask.
- All plan items verified complete. Plan file `plans/plan.md` pruned to summary.

### Wave M Completed (May 2026)
All Wave M implementation plan items verified and completed:
- 4 Critical bug fixes
- 10 High-priority documentation fixes
- 12 Medium-priority documentation fixes
- 14 Low-priority improvements

Plan file pruned to summary status - detailed implementation steps removed.

### Wave L Completed (May 2026)
All 8 module reviews completed and implementation fixes applied:

| Module | Issues Found | Priority | Status |
|--------|-------------|----------|--------|
| Core | Webhook.secret plain text, Post.user_id false doc, missing indexes | High | ✅ Fixed |
| Services | TAG_CACHE_TTL wrong (60 vs 300), backup naming docs, slug signature | Medium | ✅ Fixed |
| Routes | Preview route security (HMAC + session) | Medium | ✅ Fixed |
| Tasks | Scheduler SMTP disable logic (disabled all jobs, not just newsletter) | High | ✅ Fixed |
| Infrastructure | Missing logger in webhooks.py | Critical | ✅ Fixed |
| Frontend | mobile-menu.jsx syntax error, srcset undefined in search.html | Critical | ✅ Fixed |
| Deployment | celery concurrency missing, pip-audit silenced, webhook encryption path | Medium | ✅ Fixed |
| Testing | clean_analytics_cache import inconsistency | Low | ✅ Verified |

**Total: 1 critical bug fixed, 2 high priority bugs fixed, 5 medium/low issues fixed**

### Wave K Completed (May 2026)
Architecture reviews documented in `plans/<module>_review.md`:

| Module | Issues Found | Status |
|--------|-------------|--------|
| Core | Backup codes count (8 vs 10), AdminSession index | ✅ Fixed |
| Services | **Critical**: run_daily_backup() retention bug (backup_*.db vs blog_*.db) | ✅ Fixed |
| Routes | Preview route security (HMAC + session required) | ✅ Fixed |
| Tasks | None | ✅ Verified |
| Infrastructure | Redis/celery health checks undocumented | ✅ Fixed |
| Frontend | None | ✅ Verified |
| Deployment | Encryption type (AES-256-GCM confirmed) | ✅ Verified |
| Testing | None | ✅ Verified |

### Critical Bugs Fixed (Wave L)

1. **webhooks.py missing logger** (`app/webhooks.py:111`) - NameError at runtime
2. **mobile-menu.jsx syntax error** (`app/static/js/shared/mobile-menu.jsx:42`) - Extra `});` caused parse failure
3. **search.html srcset undefined** (`app/templates/search.html:31`) - Missing variable
4. **scheduler.py SMTP disable logic** (`app/scheduler.py:269-271`) - Entire scheduler disabled instead of just newsletter

### Key Verification Results (Wave K)
- All routes match documented paths
- All function signatures match documentation
- All configuration values verified
- All Celery queue names and line numbers correct
- All APScheduler schedules correct

### Remaining Known Issues (None - All Fixed)

All Wave K and Wave L issues have been resolved:
- Webhook.secret encryption - IMPLEMENTED
- TAG_CACHE_TTL - FIXED
- Backup retention bug - FIXED
- mobile-menu.jsx syntax error - FIXED
- search.html srcset - FIXED
- scheduler.py SMTP disable logic - FIXED
- webhooks.py missing logger - FIXED