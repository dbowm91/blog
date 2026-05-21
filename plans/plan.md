# Implementation Plan - Blog CMS

**Project:** Blog CMS
**Status:** ACTIVE - Wave K: Architecture Review Phase
**Last Updated:** May 2026

---

## Overview

This is the consolidated implementation plan for the Blog CMS project. It serves as the single source of truth for:
- Completed implementation waves (A-J)
- Wave K: Pending architecture reviews (8 modules)
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

## Wave K: Architecture Reviews (IN PROGRESS)

**Status:** IN PROGRESS (May 2026)
**Goal:** Verify architecture documentation against implementation, document discrepancies, identify bugs

### Wave K Organization

Reviews are organized into **three parallel groups** based on module independence. Groups K1, K2, and K3 can execute in parallel:

| Group | Modules | Parallel Execution |
|-------|---------|---------------------|
| K1 (Independent Core) | Core, Services | Can run in parallel with K2, K3 |
| K2 (Application Layer) | Routes, Tasks | Can run in parallel with K1, K3 |
| K3 (Infrastructure) | Frontend, Testing, Infrastructure, Deployment | Can run in parallel with K1, K2 |

### Wave K Subagent Execution Strategy

**Phase 1 (Parallel):** Launch subagents for K1a and K1b
**Phase 2 (Parallel):** Launch subagents for K2a and K2b
**Phase 3 (Parallel):** Launch subagents for K3a, K3b, K3c, K3d

Each subagent should create a branch: `wave-k-{group}-{description}`

---

## K1a: Core Module Architecture Review

**Branch:** `wave-k1-core`

### Focus Areas
- App factory pattern implementation
- Configuration management (config.py)
- Model definitions, relationships, and extensions

### Documents to Review
- `architecture/core/app-factory.md`
- `architecture/core/configuration.md`
- `architecture/core/models.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/__init__.py` | App factory, create_app() |
| `app/config.py` | Configuration management |
| `app/models.py` | All model definitions (User, Post, Comment, etc.) |
| `app/extensions.py` | Flask extensions initialization |

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

### Tasks
1. Read all architecture documents for Routes module
2. Cross-reference with actual code in `app/routes/`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/routes_review.md`

---

## K2b: Tasks Module Architecture Review

**Branch:** `wave-k2-tasks`

### Focus Areas
- Celery task definitions and queue routing
- APScheduler job schedules and execution
- Task error handling and retries

### Documents to Review
- `architecture/tasks/celery-tasks.md`
- `architecture/tasks/scheduler.md`
- `architecture/tasks/overview.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/tasks.py` | All Celery task definitions |
| `app/scheduler.py` | APScheduler job definitions |
| `app/celery_app.py` | Celery app configuration |

### Verified Details for Reference

**APScheduler Job Schedules (app/scheduler.py):**
| Job | Schedule | Line |
|-----|----------|------|
| `cleanup_expired_subscribers` | `minute="*/5"` (every 5 min) | 285 |
| `run_daily_backup` | `hour=2, minute=0` (2 AM) | 299 |

**Celery Queue Names (app/tasks.py):**
| Queue | Task | Line |
|-------|------|------|
| `images` | `generate_image_variants` | 31 |
| `newsletter` | `send_newsletter_task` | 130 |
| `webhooks` | `deliver_webhook_task` | 182 |
| `email` | `send_confirmation_task` | 255 |
| `email` | `send_password_reset_task` | 276 |
| `backup` | `run_backup_task` | 297 |

**Newsletter Retry Logic:**
- Default retry count: 5 (not 3)
- Uses `NEWSLETTER_MAX_RETRY_ATTEMPTS` config

**APScheduler Multi-Worker Limitation:**
- APScheduler jobs use FileLock which only works on a single machine
- In multi-container deployments, without external coordination (Redis, etcd), jobs may run on all replicas simultaneously

### Tasks
1. Read all architecture documents for Tasks module
2. Cross-reference with actual code in `app/tasks.py`, `app/scheduler.py`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/tasks_review.md`

---

## K3a: Frontend Module Architecture Review

**Branch:** `wave-k3-frontend`

### Focus Areas
- Vite build configuration and code splitting
- JavaScript/CSS asset management
- Jinja2 template structure and filters
- Theme customization support

### Documents to Review
- `architecture/frontend/static-assets.md`
- `architecture/frontend/templates.md`
- `architecture/frontend/overview.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/static/` | JavaScript, CSS assets |
| `app/templates/` | Jinja2 templates |
| `vite.config.js` | Vite build configuration |
| `app/filters.py` | Template filters |
| `app/context_processors.py` | Context processors |

### Verified Details for Reference

**Vite Configuration (vite.config.js:14-19):**
- Code splitting with `manualChunks`
- Chunks: 'vendor', 'admin', 'public'

**Template Filters (app/filters.py):**
| Filter | Purpose |
|--------|---------|
| `markdown_safe` | Safe markdown rendering |
| `reading_time` | Calculate reading time |
| `sanitize_css` | CSS sanitization |
| `post_image_url` | Post image URL generation |
| `post_image_srcset` | Srcset for responsive images |
| `post_image_avif_url_stub` | AVIF URL stub (returns None until AVIF implemented) |

**Context Processor Function Names (app/context_processors.py):**
| Function | Injects |
|----------|---------|
| `inject_csrf()` | `csrf_token`, `csp_nonce` |
| `inject_config()` | Site config variables |
| `inject_theme()` | Theme settings, `custom_css` |
| `inject_footer_data()` | Footer links and data |
| `inject_show_footer_posts()` | `show_footer_posts` boolean |

**JS Module Initialization Pattern:**
```javascript
export default function initXxx() { ... }
```

### Tasks
1. Read all architecture documents for Frontend module
2. Cross-reference with actual code in `app/static/`, `app/templates/`, `vite.config.js`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/frontend_review.md`

---

## K3b: Testing Module Architecture Review

**Branch:** `wave-k3-testing`

### Focus Areas
- Test suite organization and fixtures
- Test isolation and cleanup
- Coverage and edge cases
- E2E testing approach

### Documents to Review
- `architecture/testing/test-suite.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `tests/` | All test files (flat structure, no unit/integration subdirs) |
| `tests/conftest.py` | Test configuration and fixtures |
| `tests/shared_fixtures.py` | Shared fixtures |
| `tests/test_e2e.py` | E2E tests with classes |

### Verified Details for Reference

**Test Structure:**
- Flat `tests/` directory (no unit/integration subdirs)
- `test_e2e.py` contains E2E tests with classes

**Page View Buffer Test Protection (tests/shared_fixtures.py:6-11):**
```python
@pytest.fixture(autouse=True)
def ensure_buffer_disabled():
    """Ensure page view buffer is disabled during tests."""
    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    shutdown_page_view_buffer()
    yield
    shutdown_page_view_buffer()
```

**Test Database Session Issues:**
- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`

### Tasks
1. Read all architecture documents for Testing module
2. Cross-reference with actual code in `tests/`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/testing_review.md`

---

## K3c: Infrastructure Module Architecture Review

**Branch:** `wave-k3-infrastructure`

### Focus Areas
- Webhook delivery and retry logic
- Search provider implementation (FTS5, SQLite)
- Email sending and newsletter delivery
- Storage and file handling

### Documents to Review
- `architecture/infrastructure/webhooks.md`
- `architecture/infrastructure/search.md`
- `architecture/infrastructure/email.md`
- `architecture/infrastructure/storage.md`
- `architecture/infrastructure/overview.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `app/webhooks.py` | Webhook delivery and event creation |
| `app/email.py` | Email sending |
| `app/storage.py` | File storage |
| `app/search.py` | FTS5 search implementation |
| `app/services/search/` | Search provider abstraction |

### Verified Details for Reference

**Search Abstraction (app/services/search/):**
- `SearchProvider` abstract class with `@abstractmethod` decorators
- `SQLiteSearchProvider` - wraps existing FTS5 functionality in `app/search.py`
- `PostgreSQLSearchProvider` - stub for future implementation
- `get_search_provider()` - factory function based on `SEARCH_PROVIDER` config

**Snippet Batching (app/search.py:298):**
```python
_SQLITE_MAX_VARS = 500  # Maximum variables per query

# Batch processing pattern:
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

**Webhook Event Triggering Pattern:**
```python
# Post publish/unpublish (app/routes/api/posts.py:294-295)
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation (app/routes/public/subscribe.py:147-148)
sub.confirmed = True
# ... after commit ...
create_webhook_event(...)
```

**Deprecated Function:**
- `deliver_webhook()` in `app/webhooks.py` is deprecated (lines 55-59)
- Use `deliver_webhook_task` Celery task instead

### Tasks
1. Read all architecture documents for Infrastructure module
2. Cross-reference with actual code in `app/`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/infrastructure_review.md`

---

## K3d: Deployment Module Architecture Review

**Branch:** `wave-k3-deployment`

### Focus Areas
- Docker configuration and image size
- Security measures (HMAC, rate limiting, 2FA)
- CI/CD pipeline configuration
- Nginx and reverse proxy setup

### Documents to Review
- `architecture/deployment/docker.md`
- `architecture/deployment/security.md`
- `architecture/deployment/cicd.md`
- `architecture/deployment/overview.md`

### Code to Cross-Reference
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Docker compose configuration |
| `Dockerfile` | Docker image build |
| `nginx/` | Nginx configuration |

### Verified Details for Reference

**Brotli Compression (nginx/nginx.conf:26-34):**
- Nginx configuration includes commented Brotli settings
- Requires custom nginx image with `--with-http_brotli_module`

**Health Check Critical Checks (app/routes/public/meta.py:286-289):**
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

**Referrer-Policy Mismatch:**
- Flask sets one value, nginx sets another
- Documented but not yet fixed

### Tasks
1. Read all architecture documents for Deployment module
2. Cross-reference with actual code in `docker-compose.yml`, `Dockerfile`, `nginx/`
3. Document verification results
4. Identify bugs and improvement opportunities
5. Write final improvement plan to `plans/deployment_review.md`

---

## Wave K Completion Criteria

- All 8 module reviews completed
- All discrepancies documented with specific file:line references
- Priority classification for each issue (Critical/High/Medium/Low)
- PR created with all review findings

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

*Last updated: May 2026 - Consolidated from prior plan files*
*All completed items verified against codebase May 2026*
*Pending reviews: Wave K (8 modules)*