# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE L - Implementation Phase
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. Wave L consolidates findings from Wave K architecture reviews (8 modules) into actionable items organized by parallelization potential.

### Wave Summary

| Wave | Description | Items | Status |
|------|-------------|-------|--------|
| A-J | Implementation waves (2FA, Rate Limiting, Search, etc.) | 61+ | COMPLETED |
| K | Architecture Reviews (8 modules) | All 8 | COMPLETED |
| L | Wave K Findings Implementation | TBD | IN PROGRESS |

---

## Wave L: Architecture Review Findings Implementation

Items consolidated from 8 module reviews (core, services, routes, tasks, frontend, testing, infrastructure, deployment).

### Phase 1: Critical Bugs (Sequential - Required First)

These bugs affect security, correctness, or break functionality. Fix these before any parallel work.

#### L-1.1: Fix mobile-menu.jsx Syntax Error (CRITICAL)
**File:** `app/static/js/shared/mobile-menu.jsx:36-42`

**Issue:** Line 39-40 has incorrect structure. The `if (hamburger && nav)` block at line 36-40 is missing its closing `}` before the `});` at line 42. The structure shows:
```javascript
// Line 36-40 (current - broken):
        if (hamburger && nav) {
            hamburger.setAttribute('aria-expanded', 'false');
            nav.classList.remove('open');
        }  // Missing closing brace for this if!
// Line 42:
        });
    });
}
```

**Fix:** Add closing `}` after line 40:
```javascript
// Lines 36-43 CORRECT:
        if (hamburger && nav) {
            hamburger.setAttribute('aria-expanded', 'false');
            nav.classList.remove('open');
        }
    });
    });
}
```

**Note:** The review at `plans/frontend_review.md:81-108` correctly identifies this issue and shows the proper fix structure.

**Verification:** After fix, mobile menu should work on mobile viewport testing.

---

#### L-1.2: Webhook Logger Already Defined (VERIFIED - No Action Needed)
**File:** `app/webhooks.py:13`

**Status:** Verified - `logger = logging.getLogger(__name__)` is already defined at module level. The review at `plans/infrastructure_review.md` incorrectly flagged this as missing. No fix required.

**Verification:** Already working correctly - logger is properly defined before use at line 114.

---

#### L-1.3: Fix Preview Route Security (CRITICAL)
**File:** `app/routes/public/posts.py:94-129`

**Issue:** Documentation stated HMAC-only auth, but actual code requires BOTH HMAC token AND admin session (`session.get('admin_user_id')`).

**Fix:** Update documentation in `architecture/routes/public-routes.md:57-60`:
```markdown
# Lines 57-60 FROM:
Auth: HMAC token-based (no login required)

# TO:
Auth: HMAC token-based AND admin session verification required.
The preview route requires both a valid HMAC token AND an active admin session.
```

**Verification:** Preview route should work with valid HMAC + session; should 403 without session.

---

#### L-1.4: Encrypt Webhook.secret at Rest (HIGH)
**File:** `app/models.py:490`

**Issue:** `Webhook.secret` stored in plain text (not encrypted like `User.totp_secret`).

**Fix Pattern:** Follow `User.totp_secret` encryption pattern:
1. Add `webhook_secret_encrypted` column to Webhook model
2. Add property getter/setter that encrypt/decrypt using `app/services/encryption.py`
3. Update all code accessing `webhook.secret` to use the property
4. Update `architecture/core/models.md:172` documentation

**Implementation Details:**
```python
# In app/models.py, add to Webhook model:
webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)

@property
def secret(self) -> str:
    if self.webhook_secret_encrypted:
        return decrypt_secret(self.webhook_secret_encrypted)
    return None  # Or handle legacy plain text

@secret.setter
def secret(self, value: str) -> None:
    self.webhook_secret_encrypted = encrypt_secret(value)
```

**Note:** Requires `WEBHOOK_ENCRYPTION_KEY` config (similar to `BACKUP_ENCRYPTION_KEY`).

---

#### L-1.5: Fix Newsletter Silent Retry Loop (HIGH)
**File:** `app/scheduler.py:70-141`

**Issue:** Posts failing newsletter delivery become permanently stuck after `NEWSLETTER_MAX_RETRY_ATTEMPTS` (5) failures with no admin visibility.

**Fix Options:**
1. Log warning when posts are excluded from newsletter queue
2. Add admin dashboard visibility for stuck posts
3. Add `newsletter_failed_at` timestamp to track stuck posts

**Minimal Fix (immediate):** Add logging at exclusion point:
```python
# Around line 130 in scheduler.py, after filtering
excluded_count = len([p for p in all_posts if p.newsletter_attempts >= NEWSLETTER_MAX_RETRY_ATTEMPTS])
if excluded_count > 0:
    app.logger.warning(
        "Newsletter: %d posts excluded after %d retry attempts",
        excluded_count, NEWSLETTER_MAX_RETRY_ATTEMPTS
    )
```

**Verification:** Admin should see warning in logs about stuck posts.

---

### Phase 2: High-Priority Fixes (Can Parallelize with Phase 1)

#### L-2.1: search.html srcset Already Defined (VERIFIED - No Action Needed)
**File:** `app/templates/search.html:27`

**Status:** Verified - `srcset` variable is properly defined at line 27 with `{% set srcset = post|post_image_srcset %}` before being used at line 32. The review at `plans/frontend_review.md` incorrectly flagged this as missing. No fix required.

**Verification:** Already working correctly.

---

#### L-2.2: APScheduler SMTP Handling Already Correct (VERIFIED - No Action Needed)
**File:** `app/scheduler.py:271-281`

**Status:** Verified - When SMTP_HOST is not configured, only the newsletter job is disabled. The cleanup, publish, and backup jobs are added unconditionally after the SMTP check (lines 282-302). This matches the documented AGENTS.md behavior. The review at `plans/tasks_review.md` incorrectly flagged this as needing a fix. No code change required.

**Note:** The `plans/tasks_review.md:183-203` recommended a fix but the code already works correctly. Only the newsletter job is gated on SMTP_HOST.

---

#### L-2.3: Fix clean_analytics_cache Import in Benchmarks (HIGH)
**File:** `tests/benchmarks/conftest.py:95-96`

**Issue:** Uses different import path than main conftest:
```python
# Benchmarks (wrong):
from app.routes.admin.helpers.analytics import _clear_analytics_cache
from app.routes.admin.helpers.dashboard import _clear_dashboard_cache

# Main conftest (correct):
from app.routes.admin import _analytics_cache
```

**Fix:** Update benchmarks conftest to import from same location as main conftest, OR centralize in `shared_fixtures.py`.

**Recommendation:** Move `clean_analytics_cache` to `shared_fixtures.py` and have both conftest files import from there.

---

#### L-2.4: Fix Webhook Encryption Documentation Path (LOW)
**File:** `architecture/deployment/security.md:56`

**Issue:** Documentation says webhook encryption uses `app/backup_encryption.py` but it actually uses `app/webhook_encryption.py`.

**Fix:**
```markdown
# FROM:
Webhook secrets: AES-256-GCM via `app/backup_encryption.py` (same scheme)

# TO:
Webhook secrets: AES-256-GCM via `app/webhook_encryption.py` (direct 32-byte key, not PBKDF2)
```

---

### Phase 3: Documentation & Minor Fixes (Can Parallelize)

#### L-3.1: Fix Tag Cache TTL Default (MEDIUM)
**File:** `architecture/services/tag_cache.md:11`

**Issue:** Docs say default is 300 seconds, actual is 60 seconds.

**Fix:**
```markdown
# FROM:
- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 300 seconds / 5 minutes)

# TO:
- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 60 seconds)
```

---

#### L-3.2: Fix Slug Service Documentation Signature (MEDIUM)
**File:** `architecture/services/slug.md:15-21`

**Issue:** Documentation parameter names don't match implementation.

**Fix:**
```markdown
# FROM:
def generate_unique_slug(base_slug: str, model_class: type, exclude_id: Optional[int] = None) -> str:

# TO (match actual implementation):
def generate_unique_slug(model: Type, title: str, exclude_id: Optional[int] = None, slug: Optional[str] = None) -> str:
```

---

#### L-3.3: Fix Backup Retention Documentation (MEDIUM)
**Files:** `architecture/services/backup.md:53-56`, `architecture/tasks/scheduler.md:49`

**Issue:** Documentation claims APScheduler `run_daily_backup()` manages `backup_*.db` files, but code uses `blog_*.db`.

**Fix (backup.md):**
```markdown
# FROM:
- **Own retention**: Manages `backup_*.db` files separately from `cleanup_old_backups()`

# TO:
- **Own retention**: Manages `blog_*.db` files using the same pattern as `cleanup_old_backups()`
```

**Fix (scheduler.md):**
```markdown
# FROM:
"...which also uses `blog_*.db` naming but supports compression and encryption via `create_backup()`."

# TO:
"...which also uses `blog_*.db` naming but supports compression via `create_backup()` (encryption is disabled)."
```

---

#### L-3.4: Fix Queue Line Numbers (LOW)
**Files:** `architecture/tasks/scheduler.md:55-61`, `architecture/infrastructure/webhooks.md:115-118`

**Issue:** Line numbers in documentation don't match actual code.

**Fix:**
```markdown
# Queue routing table line numbers:
| `images` | app/tasks.py:31 |
| `newsletter` | app/tasks.py:130 |
| `webhooks` | app/tasks.py:182 |
| `email` | app/tasks.py:255,276 |
| `backup` | app/tasks.py:297 |
```

---

#### L-3.5: Fix Post Model Documentation (MEDIUM)
**File:** `architecture/core/models.md:39`

**Issue:** Documentation claims `Post` has `user_id` field pointing to User.

**Fix:** Remove false claim - `Post` model does NOT have a `user_id` field.

---

#### L-3.6: Add Missing Post Fields to Documentation (LOW)
**File:** `architecture/core/models.md:247-271`

**Issue:** `image` and `image_alt_text` fields missing from Post model docs.

**Fix:** Add to Post model documentation section.

---

#### L-3.7: Add Missing Indexes to Documentation (LOW)
**File:** `architecture/core/models.md`

**Issue:** Missing indexes documented in code:
- `ix_page_views_post_created` (post_id, created_at)
- `ix_share_events_post_created` (post_id, created_at)
- `ix_share_events_platform` (platform)
- `ix_pages_published_slug` (published, slug)

**Fix:** Add missing indexes to documentation.

---

#### L-3.8: Fix prism.min.js Location (LOW)
**File:** `architecture/frontend/static-assets.md:35`

**Issue:** Documentation says prism.min.js is in `lib/` but it's at `app/static/js/prism.min.js` (root level).

**Fix:** Update directory structure documentation.

---

#### L-3.9: Fix _breadcrumbs.html Documentation (LOW)
**File:** `architecture/frontend/templates.md:9`

**Issue:** Documentation says `app/templates/_breadcrumbs.html` exists but only `admin/_breadcrumbs.html` exists.

**Fix:** Update to note only admin version exists, or create generic version.

---

#### L-3.10: Fix API Routes Documentation (MEDIUM)
**File:** `architecture/routes/api-routes.md`

**Fixes:**
1. Line 13: Change `POST /api/subscribers/<id>` to `DELETE /api/subscribers/<int:subscriber_id>`
2. Line 12: Remove `POST /api/subscribers/export` (doesn't exist in API)
3. Add `POST /api/posts` to endpoints table
4. Document rate limits for subscriber endpoints

---

#### L-3.11: Fix Admin Routes Documentation (MEDIUM)
**File:** `architecture/routes/admin-routes.md`

**Fixes:**
1. Line 105: Fix revisions route to match actual (`GET /admin/posts/<int:post_id>/revisions`)
2. Line 98: Clarify bulk route is at `/admin/bulk` (not `/admin/posts/bulk`)

---

#### L-3.12: Add [search] Section to Config Documentation (LOW)
**File:** `architecture/core/configuration.md`

**Issue:** TOML example config missing `[search]` section.

**Fix:** Add `[search]` section to example config structure.

---

### Phase 4: CI/CD & Deployment Fixes

#### L-4.1: Add Celery Worker Concurrency (MEDIUM)
**File:** `docker-compose.yml:38`

**Issue:** No `--concurrency` flag, Celery defaults may cause memory issues.

**Fix:**
```yaml
command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

**Memory Context:** Celery is limited to 256M; concurrency=1 prevents memory issues.

---

#### L-4.2: Remove pip-audit Silencing (MEDIUM)
**File:** `.github/workflows/test.yml:94`

**Issue:** `|| true` silences pip-audit failures.

**Fix:**
```yaml
# FROM:
- name: Run pip-audit
  run: pip-audit || true

# TO:
- name: Run pip-audit
  run: pip-audit --fail-on=all
```

---

#### L-4.3: Document All Lock Files (LOW)
**File:** `architecture/tasks/scheduler.md:69`

**Issue:** Documentation only mentions `newsletter.lock`.

**Fix:**
```markdown
OLD: Lock file locations: `{instance_path}/{job_name}.lock` (e.g., `newsletter.lock`)
NEW: Lock file locations: `{instance_path}/{job_name}.lock`
     - `newsletter.lock` - Daily newsletter sending
     - `cleanup.lock` - Expired subscriber cleanup
     - `scheduled.lock` - Scheduled post publishing
     - `backup.lock` - Daily backup
```

---

#### L-4.4: Add Health Check Documentation (LOW)
**File:** `architecture/deployment/docker.md`

**Recommendation:** Add section documenting:
- `/health` endpoint returns JSON with component status
- Does not require authentication (network-level access only)
- Rate limited at nginx level
- Returns 200 even if optional services degraded (only critical checks affect status)
- Critical checks: `database`, `scheduler`, `search`, `disk_space`, `db_integrity`

---

#### L-4.5: Document Backup Encryption Key Requirements (LOW)
**Files:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`

**Recommendation:** Add clarity:
- `BACKUP_ENCRYPTION_KEY` must be at least 12 characters
- `WEBHOOK_ENCRYPTION_KEY` must be exactly 32 bytes
- Generation: `python -c "import secrets; print(secrets.token_hex(32))"`

---

#### L-4.6: Add Resource Limit Documentation (LOW)
**File:** `architecture/deployment/docker.md`

**Recommendation:** Document memory limits:
- blog: 512M limit, 256M reservation
- celery: 256M limit
- redis: 128M limit

---

### Phase 5: Future Improvements (Not Immediate)

#### L-5.1: Consider SMTP Connectivity Health Check (LOW)
**File:** `app/routes/public/meta.py`

**Issue:** Health check doesn't test actual SMTP connectivity.

**Recommendation:** Add actual SMTP test in optional checks.

---

#### L-5.2: Newsletter Retry Admin Visibility (LOW)
**File:** `app/scheduler.py:130-139`

**Issue:** Posts hitting max retries are silently excluded.

**Recommendation:** Add admin dashboard visibility for stuck newsletter posts.

---

#### L-5.3: Webhook Event Delivery Status (LOW)
**File:** `app/tasks.py:247-248`

**Issue:** Event marked delivered if ANY webhook succeeds, even if others fail.

**Recommendation:** Consider `partial_failure` status or ALL-must-succeed logic.

---

## Parallelization Strategy

### Phase 1 (Critical) - Sequential
Must fix before parallel work due to security/correctness:
- L-1.1, L-1.2, L-1.3, L-1.4, L-1.5

### Phase 2 (High) - Can Parallelize After Phase 1
- L-2.1, L-2.2, L-2.3, L-2.4

### Phase 3 (Documentation) - Can Parallelize (Multiple Agents)
All documentation fixes can run in parallel:
- L-3.1 through L-3.12

### Phase 4 (CI/CD) - Can Parallelize with Phase 3
- L-4.1, L-4.2, L-4.3, L-4.4, L-4.5, L-4.6

### Phase 5 (Future) - Backlog
Items for future consideration, not immediate implementation.

---

## Files Requiring Changes Summary

| Priority | Items | Files |
|----------|-------|-------|
| Critical | L-1.1 to L-1.5 | mobile-menu.jsx, webhooks.py, public-routes.md, models.py, scheduler.py |
| High | L-2.1 to L-2.4 | search.html, scheduler.py, benchmarks/conftest.py, security.md |
| Medium | L-3.1 to L-3.12 | tag_cache.md, slug.md, backup.md, scheduler.md, models.md, api-routes.md, admin-routes.md, configuration.md, static-assets.md, templates.md |
| Deployment | L-4.1 to L-4.6 | docker-compose.yml, test.yml, scheduler.md, docker.md |
| Future | L-5.1 to L-5.3 | meta.py, scheduler.py, tasks.py |

---

## Verification Checklist

After implementation, verify:
- [ ] Mobile menu works on mobile viewport (L-1.1)
- [x] Webhook failures log properly - already working (L-1.2)
- [x] srcset is defined in search.html - already working (L-2.1)
- [x] Cleanup/backup jobs run without SMTP - already working (L-2.2)
- [ ] Webhook secrets encrypted at rest (L-1.4)
- [ ] Newsletter stuck posts visible in logs (L-1.5)
- [ ] Benchmark tests use correct import paths (L-2.3)

---

*Last updated: May 2026 - Wave L in progress*