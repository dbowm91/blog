# Implementation Plan - Blog CMS

**Project:** Blog CMS
**Status:** COMPLETED - All waves A-K complete
**Last Updated:** May 2026

---

## Overview

This is the consolidated implementation plan for the Blog CMS project. It serves as the single source of truth for:
- Completed implementation waves (A-K)
- Key implementation details verified against the codebase
- Important patterns and conventions for future agents
- Guidance for creating new implementation waves

**Consolidation Note:** This file was created by merging all prior plan files into a single actionable plan. All claims have been verified against the actual codebase (May 2026).

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
| J | Architecture Review Fixes | 39+ | COMPLETED |

**Total: 61+ items completed**

---

## Wave K: Architecture Reviews (COMPLETED)

**Status:** COMPLETED (May 2026)
**Goal:** Verify architecture documentation against implementation, document discrepancies, identify bugs

### Wave K Summary

All 8 module reviews were completed. Reviews identified 1 critical bug (backup retention), 6 documentation discrepancies, and multiple missing documentation items. All issues were fixed during Wave J.

| Module | Branch | Issues Found | Status |
|--------|--------|-------------|--------|
| Core | `wave-k1-core` | 6 doc discrepancies, 15+ missing docs | FIXED |
| Services | `wave-k2-services` | 1 critical bug (retention), 4 doc issues | FIXED |
| Routes | `wave-k3-routes` | 9 route inaccuracies, 20+ missing routes | FIXED |
| Tasks | `wave-k4-tasks` | 4 inaccurate claims, 5 missing docs | FIXED |
| Frontend | `wave-k5-frontend` | 2 inaccurate claims, 8 missing docs | FIXED |
| Testing | `wave-k6-testing` | 4 inaccurate claims, 7 missing docs | FIXED |
| Infrastructure | `wave-k7-infrastructure` | 3 inaccurate claims, 6 missing docs | FIXED |
| Deployment | `wave-k8-deployment` | 6 inaccurate claims, 6 missing docs | FIXED |

**Total Issues Fixed:** 1 critical bug, 35+ documentation corrections

### Detailed Review Reports

All review reports are saved in `architecture/plans/`:
- `core_review.md` - App factory, configuration, models review
- `services_review.md` - Backup, slug, serialization, tag services review
- `routes_review.md` - Public, admin, API, RSS routes review
- `tasks_review.md` - Celery tasks and APScheduler review
- `frontend_review.md` - Static assets and templates review
- `testing_review.md` - Test suite and fixtures review
- `infrastructure_review.md` - Webhooks, search, email, storage review
- `deployment_review.md` - Docker, security, CI/CD review

### Critical Bug Fixed During Wave K

**Backup Retention Bug:** `app/services/backup.py:run_daily_backup()` created `blog_*.db` files but `cleanup_old_backups()` looked for `backup_*.db` files. Fixed by correcting the glob pattern. This bug meant daily backups were never being cleaned up.

### Key Verification Results

All architecture documentation was verified against actual source code:
- All routes match documented paths (verified 50+ routes)
- All function signatures match documentation
- All configuration values verified against config.py
- All Celery queue names and line numbers correct
- All APScheduler schedules correct
- Search abstraction layer correctly documented

### Verified Details for Reference

**User Model `__repr__` (app/models.py:119-120):**
```python
def __repr__(self) -> str:
    return f"<User id={self.id}>"  # Returns ID only - PII protection
```

**Comment Model Relationships (app/models.py:586-587):**
```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

**TOTP Secret Property (app/models.py:43-52):**
- `User.totp_secret` is a property that decrypts on access
- Decrypts `totp_secret_encrypted` column using AES-256-GCM

### Tasks
1. Read all architecture documents for Core module
2. Cross-reference with actual code in `app/`
3. Document verification results (claims confirmed or contradicted with file:line)
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/core_review.md`

---

## K1b: Services Module Architecture Review

**Branch:** `wave-k1-services`

### Focus Areas
- Backup service (encryption, compression, scheduling)
- Serialization/deserialization patterns
- Tag service logic
- Slug generation and collision handling

### Documents to Review
- `architecture/services/backup.md`
- `architecture/services/serialization.md`
- `architecture/services/tag.md`
- `architecture/services/slug.md`
- `architecture/services/overview.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/services/backup.py` | Backup creation, restoration, cleanup |
| `app/services/slug.py` | Slug generation with collision handling |
| `app/services/serialization.py` | Post/series serialization |
| `app/services/tag.py` | Tag service logic |
| `app/services/__init__.py` | Service exports |

### Verified Details for Reference

**Slug Generation (app/services/slug.py):**
- Collision limit is 100 tries before falling back to UUID suffix
- Uses `generate_unique_slug()` function

**Backup Service (app/services/backup.py):**
- `create_backup()` - Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression
- `run_daily_backup()` - Used by APScheduler, no encryption/compression
- Both use `blog_*.db` naming pattern
- `cleanup_old_backups()` handles retention for both

**Backup Encryption (app/backup_encryption.py):**
- AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation (600,000 iterations)
- NOT GPG-based

**Tag Cache Invalidation (app/tag_cache.py:52):**
```python
flask_cache.delete_memoized(_get_tag_counts_cached)
```

### Tasks
1. Read all architecture documents for Services module
2. Cross-reference with actual code in `app/services/`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/services_review.md`

---

## K2a: Routes Module Architecture Review

**Branch:** `wave-k2-routes`

### Focus Areas
- API endpoint implementation and authentication
- Admin dashboard and management routes
- Public routes (blog, subscribe, preview)
- RSS/Atom feed generation

### Documents to Review
- `architecture/routes/api-routes.md`
- `architecture/routes/admin-routes.md`
- `architecture/routes/public-routes.md`
- `architecture/routes/rss-feeds.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/routes/public.py` | Public routes (blog, subscribe) |
| `app/routes/api/` | API routes (posts, subscribers, stats, auth) |
| `app/routes/admin/` | Admin routes (dashboard, posts, tags, users) |
| `app/routes/rss.py` | RSS/Atom/JSON feed generation |
| `app/routes/errors.py` | Error handlers |

### Verified Details for Reference

**Important Routes (Verify Before Using):**
| Route | Actual Path | File:Line |
|-------|------------|------------|
| New post | `/admin/new` | `app/routes/admin/posts/editor.py:137` |
| Edit post | `/admin/edit/<id>` | `app/routes/admin/posts/editor.py:215` |
| Tag delete | `POST /admin/tags/delete/<id>` | `app/routes/admin/tags.py:87` |
| Comment submission | `POST /post/<slug>/comment` | `app/routes/public/comments.py:12` |
| Subscribe | Only `POST /subscribe` | `app/routes/public/subscribe.py:55` |
| API post publish | `PUT /api/posts/<id>` | `app/routes/api/posts.py:207` |

**2FA Routes:**
| Route | Path | File:Line |
|-------|------|------------|
| 2FA setup | `/admin/2fa/setup` | `app/routes/admin/auth.py:263` |
| 2FA verify | `/admin/2fa/verify` | `app/routes/admin/auth.py:312` |
| Backup codes | `/admin/2fa/backup-codes` | `app/routes/admin/auth.py:420` |
| Disable 2FA | `/admin/2fa/disable` | `app/routes/admin/auth.py:436` |

**Preview Route Security:**
- `/preview/<int:post_id>` requires admin session verification
- Both HMAC token AND `session.get('admin_user_id')` must exist

**Feed Endpoints (app/routes/rss.py):**
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

## Wave L: Future Enhancements

*No enhancements currently planned. Project is in maintenance mode.*

---

## Completed Implementation Summary

All waves A through K are now complete. The project has been thoroughly reviewed and all architecture documentation has been verified against actual source code.

### Key Achievements

- **61+ implementation items** completed across Waves A-J
- **1 critical bug fixed** during Wave K (backup retention)
- **35+ documentation corrections** made during Wave K
- **50+ routes verified** against actual implementation
- **All configuration values verified** against config.py

### Architecture Review Results

All 8 module reviews completed and fixes merged:
- Core: App factory, configuration, models verified
- Services: Backup, slug, serialization, tag services verified
- Routes: Public, admin, API, RSS routes verified and corrected
- Tasks: Celery tasks and APScheduler verified
- Frontend: Static assets and templates verified
- Testing: Test suite and fixtures verified
- Infrastructure: Webhooks, search, email, storage verified
- Deployment: Docker, security, CI/CD verified

### Reference Information

For verified implementation details, see the "Key Implementation Details" section below.

---

## Key Implementation Details (Verified May 2026)

### 2FA Implementation (Wave A)

**TOTP Encryption (app/services/encryption.py):**
- AES-256-GCM encryption
- `KEY_SIZE = 32` (256 bits)
- `User.totp_secret` is a property that decrypts on access

**Backup Codes (app/models.py:75-92):**
- 8 codes generated (not 10)
- SHA-256 hashed for storage
- Single-use: verified codes are removed

### Rate Limiting (Wave B)

**Location:** `app/config.py:145-152`, `app/middleware/rate_limit.py:32`
- `ADMIN_RATE_LIMITS` defines rate limits
- `AdminRateLimiter` class with Flask-Limiter integration
- `key_func=get_client_ip`

### Error Handling Fixes (Wave F)

All high-risk files have been fixed with specific exception handling:

| File | Exception Types | Line |
|------|-----------------|------|
| `app/routes/public/meta.py` | `OperationalError, ProgrammingError` | 214, 232, 248 |
| `app/email.py` | `SMTPAuthenticationError, SMTPConnectError, SMTPSenderRefused, SMTPServerDisconnected, SMTPException, OSError` | 94, 115-120, 124, 133, 136, 138 |
| `app/backup_integrity.py` | `sqlite3.Error, OSError, ValueError, TypeError` | 77-80 |
| `app/webhooks.py` | Returns `(False, str(e))` on error | 83 |
| `app/tasks.py` | Specific exceptions per task type | Multiple |
| `app/page_view_buffer.py` | `SQLAlchemyError, OSError` | 126, 189 |

---

## Previously Completed Reviews (Wave J - May 2026)

Wave J fixed documentation issues identified during architecture review. All issues were documented and corrected in the architecture documents.

### Core Documentation Fixes
- Added missing model documentation: AdminSession, Series, PostSeries, Webhook, WebhookEvent
- Verified totp_secret property documentation

### Services Documentation Fixes
- Clarified backup naming: both `create_backup()` and `run_daily_backup()` create `blog_*.db` files
- `cleanup_old_backups()` only handles `blog_*` files

### Routes Documentation Fixes
- 2FA routes corrected: `/admin/2fa/setup`, `/admin/2fa/verify`
- Series route added: `GET /series/<slug>`
- Archive route added: `GET /archive`
- Short URL route added: `GET /s/<code>`

### Tasks Documentation Fixes
- `send_daily_newsletter` runs synchronously
- FileLock details documented
- Newsletter retry logic documented

### Testing Documentation Fixes
- Directory structure corrected: flat `tests/` structure
- E2E file corrected: `test_e2e.py` with classes
- Buffer protection autouse pattern documented

---

## Security & Privacy Rules

**Critical for all agents:**

- **Log ID, not Username**: When logging user actions, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

---

## Wave Execution Pattern

When executing multi-wave implementation plans:

1. **Create separate branches** for each parallel wave to avoid conflicts
2. **Use subagents** with separate branches to parallelize work
3. **Merge to main** after each wave completes
4. **Update plan status** in plan.md after each wave

### Branch Naming Convention

```
wave-k1-core-services
wave-k2-routes-tasks
wave-k3-frontend-testing-infrastructure-deployment
```

---

## Creating New Implementation Waves

To propose a new enhancement or bug fix:

1. Create a branch: `wave-<letter>-<description>`
2. Implement the changes following existing patterns
3. Update this file with the new wave information
4. Create a PR for review

---

*Last updated: May 2026 - All waves A-K complete*
*Project in maintenance mode - all architecture documentation verified*