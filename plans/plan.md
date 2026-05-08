# Implementation Plan

**Project:** Blog CMS
**Status:** Ongoing - See individual waves
**Last Updated:** May 2026

---

## Overview

This is the consolidated implementation plan for the Blog CMS project. It contains documentation corrections (completed), code improvements (completed), and future enhancement items organized into parallelizable waves.

### How to Use This Plan

1. **Read AGENTS.md** for general context before starting any work
2. **Check module-specific AGENTS.override.md** files for specialized guidance
3. **Execute waves in order**, starting with Wave A
4. **Within each wave**, items can be executed in parallel via subagents
5. **Update this document** with completion status after each wave

---

## Part 1: Completed Work (Reference)

### Documentation Corrections (Wave A-D - COMPLETED May 2026)

All documentation corrections from the architecture review have been completed:

| Phase | Item | Status |
|-------|------|--------|
| 1.1 | Add `fail_under = 80` to pytest.ini | COMPLETED |
| 2.1 | Document slug collision limit in tag.py | COMPLETED |
| 2.2 | Document `run_daily_backup()` in backup.py | COMPLETED |
| 2.3 | Fix serialization import docs | COMPLETED |
| 3.1 | Correct APScheduler schedules (5 min, 02:00) | COMPLETED |
| 3.2 | Document queue routing and backup implementations | COMPLETED |
| 4.1-4.4 | Verify template filters and context processors | COMPLETED |
| 5.2 | Document `rebuild_fts()` and SQLite batching | COMPLETED |
| 5.3 | Document Celery queue names | COMPLETED |
| 6.1-6.3 | Update User model docs (repr, relationships, logo_text) | COMPLETED |
| 7.2 | Align security headers (X-Frame-Options, COOP) | COMPLETED |
| 8.1-8.7 | Correct route documentation | COMPLETED |
| 9.1-9.4 | Correct test directory structure and fixtures | COMPLETED |

---

## Part 2: Future Implementation Waves

The following items are planned for future implementation. They are organized into waves that can be executed in parallel where indicated.

---

### Wave A: Enhanced 2FA Security

**Priority:** High
**Parallelization:** Items within this wave can run sequentially (they build on each other)

#### A.1: TOTP Encryption for 2FA
**File:** `app/models.py`, `app/services/encryption.py` (new)

Implement TOTP encryption to secure 2FA secrets:

1. **Create encryption service** at `app/services/encryption.py`:
   ```python
   # Implement AES-256-GCM encryption for TOTP secrets
   # Use SECRET_KEY as master key
   # Store encrypted TOTP secret in User model
   ```

2. **Update User model** (`app/models.py`):
   - Add `totp_secret_encrypted` field (String, nullable)
   - Add `totp_enabled` field (Boolean, default=False)
   - Modify `__repr__` to not leak TOTP status

3. **Add TOTP verification** to login flow:
   - After password verification, check if `totp_enabled`
   - If enabled, require TOTP code before completing login
   - Use `pyotp` library for TOTP generation/verification

4. **Add admin UI** for enabling/disabling 2FA:
   - Admin settings page: "Enable Two-Factor Authentication"
   - Show QR code for authenticator app setup
   - Provide backup codes generation

**Implementation Notes:**
- Encryption key derivation: Use `secrets.token_bytes(32)` with PBKDF2
- TOTP window: Allow 1 step before/after for clock drift
- Backup codes: Generate 8 random 8-character codes, hash before storage

#### A.2: 2FA Backup Codes
**Dependencies:** A.1 must be completed first

Add backup codes for account recovery:

1. **Create backup codes model** or extend User model:
   ```python
   backup_codes_hashed = db.Column(db.JSON, nullable)  # Array of hashed codes
   ```

2. **Generate backup codes** on 2FA enable:
   - Generate 8 random codes: format `XXXX-XXXX`
   - Hash each code with SHA-256 before storage
   - Return plain codes to user for printing (one-time display)

3. **Verify backup code** during login:
   - Check TOTP first, if failed check backup codes
   - Each backup code is single-use
   - Remove used code from array after successful verification

4. **Admin UI additions:**
   - "View remaining backup codes" (requires 2FA)
   - "Regenerate backup codes" (invalidates all previous)

---

### Wave B: Rate Limiting Infrastructure

**Priority:** High
**Parallelization:** Items can be parallelized with subagents on separate branches

#### B.1: Admin Rate Limiting
**File:** `app/routes/admin/`, `app/middleware/rate_limit.py` (new)

Implement per-admin rate limiting to prevent abuse:

1. **Create rate limiting middleware** at `app/middleware/rate_limit.py`:
   ```python
   # Rate limiter using Redis (or in-memory for single-instance)
   # Track requests per admin_id or IP
   # Configurable limits per endpoint type
   ```

2. **Define rate limit configurations** in `app/config.py`:
   ```python
   ADMIN_RATE_LIMITS = {
       'login': (5, 60),        # 5 attempts per 60 seconds
       'api_write': (100, 60),  # 100 writes per minute
       'api_read': (500, 60),   # 500 reads per minute
   }
   ```

3. **Apply rate limiting** to admin routes:
   - Login endpoint: strict limit (5/min)
   - Post create/update: moderate limit (100/min)
   - Stats/analytics: higher limit (500/min)
   - Settings changes: moderate limit (50/min)

4. **Return 429 Too Many Requests** with `Retry-After` header

5. **Add logging** of rate limit hits:
   - Log admin ID, endpoint, current count
   - Alert on repeated violations

**Testing:** Requires testing 35+ admin routes for correct application

#### B.2: API Rate Limiting
**Dependencies:** B.1 establishes the infrastructure

Extend rate limiting to public API endpoints:

1. **Document rate limits** in `architecture/routes/api-routes.md`:
   - Public POST /subscribe: 10/min
   - Public comment submission: 20/min
   - API authenticated: 1000/hour

2. **Implement per-key rate limiting** for API:
   - Use API key or session as identifier
   - Different limits for authenticated vs anonymous

---

### Wave C: Search Infrastructure

**Priority:** Medium
**Parallelization:** Items within this wave are independent

#### C.1: PostgreSQL FTS Abstraction
**Files:** `app/search.py`, `app/models.py`, `app/services/search.py` (new)

Abstract SQLite FTS5 to support PostgreSQL full-text search:

1. **Create search service interface** at `app/services/search.py`:
   ```python
   class SearchProvider(ABC):
       @abstractmethod
       def search(query: str, limit: int = 20) -> list[dict]: ...
       @abstractmethod
       def index_post(post: Post) -> None: ...
       @abstractmethod
       def remove_post(post_id: int) -> None: ...
       @abstractmethod
       def rebuild_index() -> None: ...
   ```

2. **Implement SQLite FTS5 provider** (current implementation):
   - Move current FTS5 logic from `app/search.py` to `app/services/search/sqlite.py`
   - Ensure `rebuild_fts()` and `get_search_snippets()` work correctly

3. **Implement PostgreSQL FTS provider**:
   - Use `tsvector` and `tsquery` for full-text search
   - Use `ts_rank` for relevance scoring
   - Support phrase search with `<->` operator

4. **Add configuration** in `app/config.py`:
   ```python
   SEARCH_PROVIDER = 'sqlite'  # or 'postgresql'
   SEARCH_CONFIG = {  # PostgreSQL-specific
       'weights': {'A': 10, 'B': 5, 'C': 2, 'D': 1}
   }
   ```

5. **Update search routes** to use abstraction:
   - `app/routes/public/search.py` - use `search_provider.search()`
   - `app/routes/api/posts.py` - use `search_provider.index_post()`

6. **Migration strategy** for existing data:
   - Export from SQLite FTS5
   - Import to PostgreSQL tsvector
   - Provide CLI command: `flask search migrate-to-pg`

**Implementation Notes:**
- Snippet batching: Use `chunk_size = 500` for SQLite parameter limits
- Result caching: Cache frequent searches for 5 minutes
- Relevance tuning: Weights affect ranking (A=title, B=summary, C=body, D=tags)

---

### Wave D: Frontend Enhancements

**Priority:** Medium (Frontend scope)
**Parallelization:** Independent files, can use subagents

#### D.1: Vite Code Splitting
**Files:** `app/static/js/`, `vite.config.js`, `app/templates/`

Implement route-based code splitting with Vite:

1. **Update vite.config.js** to enable splitting:
   ```javascript
   build: {
     rollupOptions: {
       output: {
         manualChunks: {
           'vendor': ['vue', 'vue-router', 'pinia'],
           'admin': ['./admin-app.js'],
           'public': ['./public-app.js'],
         }
       }
     }
   }
   ```

2. **Identify admin routes** requiring JS:
   - Post editor (new/edit)
   - Newsletter composition
   - Settings pages

3. **Create admin entry point** `app/static/js/admin/main.js`:
   ```javascript
   import { createApp } from 'vue'
   import AdminApp from './AdminApp.vue'
   createApp(AdminApp).mount('#admin-app')
   ```

4. **Update templates** to use dynamic imports:
   ```html
   <script type="module">
     import('/static/js/admin/post-editor.js')
       .then(module => module.initEditor())
   </script>
   ```

5. **Lazy load route components**:
   ```javascript
   const PostEditor = () => import('./components/PostEditor.vue')
   ```

6. **Verify in production** build:
   ```bash
   npm run build
   # Check output size and chunking
   ```

#### D.2: AVIF Image Support
**Files:** `app/tasks.py`, `app/storage.py`, `app/models.py`

Add AVIF format support for uploaded images:

1. **Add image processing library** (pillow or imageio):
   ```bash
   pip install pillow-avif-plugin
   ```

2. **Update image variants** in `app/tasks.py`:
   - When processing upload, generate AVIF variant
   - Configurable quality (target: 80)
   - Fallback to original if AVIF fails

3. **Update storage backend** in `app/storage.py`:
   - Save AVIF to same path with `.avif` extension
   - Example: `uploads/2024/05/image.jpg.avif`

4. **Update image URLs** in `app/filters.py`:
   - Add `post_image_avif_url` filter
   - Update `post_image_url` to accept format parameter

5. **Update templates** to use AVIF with fallback:
   ```html
   <picture>
     <source srcset="{{ post.image | post_image_avif_url }}" type="image/avif">
     <source srcset="{{ post.image | post_image_url }}" type="image/jpeg">
     <img src="{{ post.image | post_image_url }}" alt="...">
   </picture>
   ```

6. **Update documentation** in `architecture/frontend/static-assets.md`

---

### Wave E: Performance & Compression

**Priority:** Medium
**Parallelization:** Independent

#### E.1: Brotli Compression for Nginx
**Files:** `nginx/conf.d/blog.conf`, `nginx/Dockerfile`

Enable Brotli compression as alternative to gzip:

1. **Install nginx-brotli module** in Dockerfile:
   ```dockerfile
   RUN apt-get install -y libbrotli-dev nginx-module-brotli
   ```

2. **Configure nginx** in `nginx/conf.d/blog.conf`:
   ```nginx
   brotli on;
   brotli_types text/html text/css application/javascript application/json;
   brotli_comp_level 6;
   ```

3. **Test compression**:
   ```bash
   curl -H "Accept-Encoding: br" -I https://blog.example.com
   # Should show Content-Encoding: br
   ```

4. **Update deployment docs** in `architecture/deployment/`

---

## Part 3: Deferred Items

These items were deferred due to scope:

| Item | Reason Deferred |
|------|-----------------|
| TOTP encryption (2FA) | Requires encryption helpers, model changes, UI |
| 2FA backup codes | Requires UI + model changes |
| Admin rate limiting | Requires testing 35+ routes |
| PostgreSQL FTS abstraction | Significant architecture change |
| Vite code splitting | Frontend scope |
| AVIF support | Frontend scope |
| Brotli compression | Nginx config |

---

## Part 4: Implementation Reference

### Wave Execution Pattern

When executing a wave with multiple items:

1. **Create wave branch**: `git checkout -b wave-x-description`

2. **For parallel items**, create sub-branches:
   ```bash
   git checkout -b wave-a-1-encryption
   git checkout -b wave-a-2-backup-codes
   ```

3. **Implement items** in parallel subagents

4. **Merge sub-branches** back to wave branch

5. **Test wave branch** thoroughly

6. **Merge to main**: `git checkout main && git merge wave-x-description`

7. **Update this plan** with completion status

### Branch Naming Convention

```
wave-a-totp-encryption
wave-b-rate-limiting
wave-c-postgres-search
wave-d-frontend
wave-e-brotli
```

### Notes for Future Agents

#### Backup Implementations
There are two separate backup implementations:
- `app/services/backup.py:create_backup()` - Celery task, `blog_*.db`, encryption/compression
- `app/scheduler.py:run_daily_backup()` - APScheduler, `backup_*.db`, no encryption/compression

#### Slug Generation
Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`).

#### APScheduler Job Schedules
- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

#### Email Retry Count
Newsletter retry count default is 5 (not 3 as some documentation may claim).

#### Context Processors
Actual context processor function names (not the injected variable names):
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

#### Template Filters
Actual filters (defined in `app/filters.py`):
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

#### Celery Queue Names
Tasks use specific queues: `images`, `newsletter`, `webhooks`, `email`, `backup` (see `app/tasks.py` lines 29, 129, 192, 264, 285, 306)

#### Actual Routes
When documenting or referring to routes, verify against actual implementation:
- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)

#### User Model `__repr__`
Returns `<User id={self.id}>` for PII/security reasons, not username.

#### Security Headers
- Flask sets `X-Frame-Options: DENY` and `Cross-Origin-Opener-Policy: same-origin`
- nginx aligned to use `DENY` and `Cross-Origin-Opener-Policy: same-origin`

#### Health Check Status Logic
Health check only considers critical checks for overall status (optional services don't affect degraded):
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

#### Snippet Batching
For SQLite parameter limits, batch post_ids:
```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

#### Webhook Event Triggering
Webhook events are triggered at key state transitions:
```python
# Post publish/unpublish in app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation in app/routes/public/subscribe.py
sub.confirmed = True
# ... after commit ...
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

#### Feed Endpoints
Three feed endpoints available:
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

### Test Fixtures
The `ensure_buffer_disabled` autouse fixture in `tests/conftest.py` (lines 185-193) handles page view buffer shutdown. Use `shutdown_page_view_buffer()` in any custom test fixtures.

### High-Risk Files (Error Handling)
These files previously used broad `except Exception` clauses. All have been replaced with specific exceptions:
- `app/routes/public/meta.py`
- `app/email.py`
- `app/backup_integrity.py`
- `app/webhooks.py`
- `app/tasks.py`
- `app/page_view_buffer.py`

---

## Plan Status

| Wave | Description | Status |
|------|-------------|--------|
| A | 2FA Security (TOTP + Backup Codes) | COMPLETED |
| B | Rate Limiting Infrastructure | COMPLETED |
| C | Search Infrastructure (PostgreSQL) | COMPLETED |
| D | Frontend Enhancements (Vite + AVIF) | COMPLETED |
| E | Performance (Brotli) | COMPLETED |

All documentation corrections (Waves A-D from previous plan) are COMPLETED.

---

*Last updated: May 2026*