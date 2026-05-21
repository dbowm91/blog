# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE L - Implementation Phase
**Last Updated:** May 2026 (Verified & Corrected)

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. Wave L consolidates findings from Wave K architecture reviews (8 modules) into actionable items organized by parallelization potential.

### Wave Summary

| Wave | Description | Items | Status |
|------|-------------|-------|--------|
| A-J | Implementation waves (2FA, Rate Limiting, Search, etc.) | 61+ | COMPLETED |
| K | Architecture Reviews (8 modules) | All 8 | COMPLETED |
| L | Wave K Findings Implementation | See below | IN PROGRESS |

---

## Wave L: Architecture Review Findings Implementation

Items verified against the codebase. Some items marked "NO ACTION NEEDED" were found to already be correct during verification.

---

## PHASE 1: Critical Bugs (Sequential - Required First)

These bugs affect security, correctness, or break functionality. Fix before any parallel work.

### L-1.1: Webhook Secret Not Encrypted at Rest (HIGH)
**File:** `app/models.py:490`

**Issue:** `Webhook.secret` is stored in plain text (not encrypted like `User.totp_secret`).

**Fix Pattern:** Follow `User.totp_secret` encryption pattern:
1. Add `webhook_secret_encrypted` column to Webhook model (LargeBinary)
2. Add property getter/setter that encrypt/decrypt using `app/services/encryption.py`
3. Update all code accessing `webhook.secret` to use the property
4. Update `architecture/core/models.md:172` documentation

**Implementation:**
```python
# In app/models.py, add to Webhook model:
webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)

@property
def secret(self) -> str:
    if self.webhook_secret_encrypted:
        return decrypt_secret(self.webhook_secret_encrypted)
    return None

@secret.setter
def secret(self, value: str) -> None:
    self.webhook_secret_encrypted = encrypt_secret(value)
```

**Note:** Requires `WEBHOOK_ENCRYPTION_KEY` config (similar to `BACKUP_ENCRYPTION_KEY`).

**Verification:** Run tests, verify webhook delivery still works.

---

### L-1.2: Newsletter Stuck Posts Visibility (MEDIUM)
**File:** `app/scheduler.py:87-100`

**Issue:** Posts that hit `NEWSLETTER_MAX_RETRY_ATTEMPTS` are excluded from the newsletter queue silently. There is no logging or admin visibility when posts are excluded.

**Fix:** Add logging when posts are excluded from the queue:
```python
# After line 100 in scheduler.py, add visibility:
excluded = [
    p for p in db.session.query(Post).filter(
        Post.published == True,
        Post.published_at.isnot(None),
        Post.newsletter_sent_at.is_(None),
        Post.newsletter_attempts >= NEWSLETTER_MAX_RETRY_ATTEMPTS
    ).all() if True  # Force query
]
if excluded:
    app.logger.warning(
        "Newsletter: %d posts excluded after %d retry attempts: %s",
        len(excluded),
        NEWSLETTER_MAX_RETRY_ATTEMPTS,
        [f"id={p.id}, title={p.title}" for p in excluded[:5]]  # Log first 5
    )
```

**Verification:** Check logs when newsletter runs with posts that have high attempt counts.

---

### L-1.3: Webhook Delivery Partial Failure (MEDIUM)
**File:** `app/tasks.py:247-248`

**Issue:** `event.delivered = delivered_count > 0` means if ANY webhook succeeds (even if 9 of 10 fail), the event is marked as delivered.

**Fix:** Consider marking delivered only if ALL webhooks succeed, or add `partial_failure` status:
```python
# Option A: Mark delivered only if all succeed
event.delivered = delivered_count == total_count

# Option B: Add partial failure tracking
if delivered_count == 0:
    event.delivery_status = 'failed'
elif delivered_count < total_count:
    event.delivery_status = 'partial_failure'
else:
    event.delivery_status = 'delivered'
```

**Verification:** Test with multiple webhooks where some fail.

---

## PHASE 2: High-Priority Fixes (Can Parallelize with Phase 1)

### L-2.1: Benchmark Conftest Cache Clear Import Mismatch (HIGH)
**File:** `tests/benchmarks/conftest.py:95-96`

**Issue:** Uses different import path than main conftest:
```python
# Benchmarks (different path):
from app.routes.admin.helpers.analytics import _clear_analytics_cache
from app.routes.admin.helpers.dashboard import _clear_dashboard_cache

# Main conftest (different path):
from app.routes.admin import _analytics_cache
```

**Fix:** Centralize `clean_analytics_cache` in `tests/shared_fixtures.py`:
1. Move implementation to `shared_fixtures.py`
2. Have both conftest files import from there
3. Ensure both use the same cache-clearing mechanism

**Verification:** Run benchmark tests, verify cache is properly cleared.

---

### L-2.2: Fix Webhook Encryption Documentation Path (LOW)
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

### L-2.3: Fix Queue Line Numbers (LOW)
**Files:** `architecture/tasks/scheduler.md:55-61`, `architecture/infrastructure/webhooks.md:115-118`

**Issue:** Line numbers in documentation don't match actual code.

**Fix:**
```markdown
| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:31` |
| `newsletter` | Newsletter delivery | `app/tasks.py:130` |
| `webhooks` | Webhook delivery | `app/tasks.py:182` |
| `email` | Transactional email | `app/tasks.py:255,276` |
| `backup` | Backup tasks | `app/tasks.py:297` |
```

---

### L-2.4: Document All Lock Files (LOW)
**File:** `architecture/tasks/scheduler.md:69`

**Issue:** Documentation only mentions `newsletter.lock`.

**Fix:**
```markdown
Lock file locations: `{instance_path}/{job_name}.lock`
- `newsletter.lock` - Daily newsletter sending
- `cleanup.lock` - Expired subscriber cleanup
- `scheduled.lock` - Scheduled post publishing
- `backup.lock` - Daily backup
```

---

## PHASE 3: Documentation Fixes (Can Parallelize - Multiple Agents)

### L-3.1: Add Missing Indexes to Documentation (MEDIUM)
**File:** `architecture/core/models.md`

**Issue:** Missing indexes documented in code:
- `ix_page_views_post_created` (post_id, created_at)
- `ix_share_events_post_created` (post_id, created_at)
- `ix_share_events_platform` (platform)

**Fix:** Add to Key Indexes section under respective models.

---

### L-3.2: Fix prism.min.js Location (LOW)
**File:** `architecture/frontend/static-assets.md:35`

**Issue:** Documentation says prism.min.js is in `lib/` but it's at `app/static/js/prism.min.js` (root level).

**Fix:** Update directory structure to show prism.min.js in `js/` root, not `lib/`.

---

### L-3.3: Fix _breadcrumbs.html Documentation (LOW)
**File:** `architecture/frontend/templates.md:9`

**Issue:** Documentation says `app/templates/_breadcrumbs.html` exists but only `admin/_breadcrumbs.html` exists.

**Fix:** Update to note only admin version exists, or create generic version.

---

### L-3.4: Fix API Routes Documentation (MEDIUM)
**File:** `architecture/routes/api-routes.md`

**Fixes:**
1. Line 12: Remove `POST /api/subscribers/export` (doesn't exist in API, only in admin)
2. Line 13: Change `POST /api/subscribers/<id>` to `DELETE /api/subscribers/<int:subscriber_id>`
3. Add `POST /api/posts` to endpoints table (exists at line 105 of posts.py)
4. Document rate limits for subscriber endpoints

---

### L-3.5: Add [search] Section to Config Documentation (LOW)
**File:** `architecture/core/configuration.md`

**Issue:** TOML example config missing `[search]` section.

**Fix:** Add `[search]` section to example config:
```toml
[search]
provider = "sqlite"  # or "postgresql"
config = {}
```

---

### L-3.6: Add Health Check Documentation (LOW)
**File:** `architecture/deployment/docker.md`

**Recommendation:** Add section documenting:
- `/health` endpoint returns JSON with component status
- Does not require authentication (network-level access only)
- Rate limited at nginx level
- Returns 200 even if optional services degraded (only critical checks affect status)
- Critical checks: `database`, `scheduler`, `search`, `disk_space`, `db_integrity`

---

### L-3.7: Document Encryption Key Requirements (LOW)
**Files:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`

**Recommendation:** Add clarity:
- `BACKUP_ENCRYPTION_KEY` must be at least 12 characters
- `WEBHOOK_ENCRYPTION_KEY` must be exactly 32 bytes
- Generation: `python -c "import secrets; print(secrets.token_hex(32))"`

---

### L-3.8: Add Resource Limit Documentation (LOW)
**File:** `architecture/deployment/docker.md`

**Recommendation:** Document actual memory limits:
- blog: 512M limit, 256M reservation
- celery: 256M limit
- redis: 128M limit

---

## PHASE 4: Future Improvements (Backlog)

These items are not immediate implementation but should be considered for future work.

### L-4.1: Consider SMTP Connectivity Health Check (LOW)
**File:** `app/routes/public/meta.py`

**Issue:** Health check doesn't test actual SMTP connectivity.

**Recommendation:** Add actual SMTP test in optional checks.

---

### L-4.2: Webhook Event Delivery Status (LOW)
**File:** `app/tasks.py:247-248`

**Recommendation:** Consider `partial_failure` status or ALL-must-succeed logic for multi-webhook scenarios.

---

## Parallelization Strategy

### Phase 1 (Critical) - Sequential
Must fix before parallel work due to security/correctness:
- L-1.1, L-1.2, L-1.3

### Phase 2 (High) - Can Parallelize After Phase 1
- L-2.1, L-2.2, L-2.3, L-2.4

### Phase 3 (Documentation) - Can Parallelize (Multiple Agents)
All documentation fixes can run in parallel:
- L-3.1 through L-3.8

### Phase 4 (Future) - Backlog
Items for future consideration, not immediate implementation:
- L-4.1, L-4.2

---

## Files Requiring Changes Summary

| Priority | Items | Files |
|----------|-------|-------|
| Critical | L-1.1, L-1.2, L-1.3 | models.py, scheduler.py, tasks.py |
| High | L-2.1 | tests/benchmarks/conftest.py, tests/shared_fixtures.py |
| Documentation | L-2.2, L-2.3, L-2.4, L-3.1-L-3.8 | security.md, scheduler.md, models.md, api-routes.md, configuration.md, docker.md, static-assets.md, templates.md |
| Future | L-4.1, L-4.2 | meta.py, tasks.py |

---

## Verified - No Action Needed

The following items were verified to already be correct in the codebase:
- **L-1.1 (mobile-menu.jsx)**: NO SYNTAX ERROR - code is syntactically correct (false positive from review)
- **L-1.2 (webhook logger)**: `logger = logging.getLogger(__name__)` already defined at module level
- **L-1.3 (preview route docs)**: Documentation already correct (both HMAC AND session required)
- **L-2.1 (search.html srcset)**: srcset properly defined at line 27 before use at line 32
- **L-2.2 (APScheduler SMTP)**: Only newsletter disabled, other jobs run unconditionally
- **L-3.1 (tag cache TTL)**: Docs already say 60 seconds
- **L-3.2 (slug signature)**: Documentation matches implementation
- **L-3.3 (backup retention)**: Documentation already correct about `blog_*.db` pattern
- **L-3.5 (Post user_id)**: Documentation does NOT claim user_id exists (correct)
- **L-3.6 (image fields)**: Documentation already shows image and image_alt_text
- **L-3.7 (admin revisions route)**: Route correctly documented
- **L-4.1 (celery concurrency)**: `--concurrency=1` already present in docker-compose.yml
- **L-4.2 (pip-audit)**: `--fail-on=all` already used in CI

---

## Verification Checklist

After implementation, verify:
- [ ] Webhook secrets encrypted at rest (L-1.1)
- [ ] Newsletter excluded posts visible in logs (L-1.2)
- [ ] Webhook partial failures handled correctly (L-1.3)
- [ ] Benchmark tests use correct cache clear path (L-2.1)
- [ ] Documentation fixes applied (L-2.2 - L-3.8)

---

## Notes for Future Agents

### Plan Item Verification
Always verify plan items against actual code. Architecture review findings may contain errors or be outdated. Several items in this plan were found to already be correct during verification.

### Critical Bug Fixes
Priority should be given to Phase 1 items (L-1.1 through L-1.3) as they affect security and correctness.

### Parallel Execution
Phase 3 documentation fixes can be executed in parallel by multiple agents. Each agent can take a subset of items (L-3.1 through L-3.8).

### Backup Implementations
There are two separate backup implementations:
- `app/services/backup.py:create_backup()` - Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression

Both use `blog_*.db` naming pattern.

### APScheduler Job Schedules
- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`)
- `run_daily_backup` runs at 02:00 UTC
- When SMTP_HOST is not configured, only the daily newsletter job is disabled

### Health Check Status Logic
Health check only considers critical checks for overall status (optional services don't affect degraded):
- Critical: `database`, `scheduler`, `search`, `disk_space`, `db_integrity`
- Optional: `backup_freshness`, `redis`, `celery`

---

*Last updated: May 2026 - Wave L verified and corrected*