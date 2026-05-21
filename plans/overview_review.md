# Overview Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** overview_reviewer

---

## 1. Verified Accurate Claims

| Claim | Overview Location | Module Verification |
|-------|-------------------|---------------------|
| Two backup implementations (Celery task vs APScheduler) | overview.md:369-371 | services_review:17, tasks_review:41 |
| Backup uses AES-256-GCM encryption with PBKDF2 (600,000 iterations) | overview.md:366 | services_review:14, deployment_review:23 |
| `blog_*.db` naming pattern for backups | overview.md:369 | services_review:15-16 |
| Slug collision max 100 before UUID fallback | overview.md:393 | services_review:26 |
| Celery queues: images, newsletter, webhooks, email, backup | overview.md:63-67 | tasks_review:12, deployment_review:18 |
| `send_daily_newsletter` in APScheduler | overview.md:441 | tasks_review:28 |
| `cleanup_expired_subscribers` every 5 minutes | overview.md:442 | tasks_review:20 |
| `publish_scheduled_posts` every 5 minutes | overview.md:443 | tasks_review:21 |
| `run_daily_backup` at 02:00 | overview.md:444 | tasks_review:22 |
| APScheduler multi-worker FileLock limitation | overview.md:446 | tasks_review:30 |
| Search abstraction with `SearchProvider` ABC | overview.md:377-386 | services_review:64-67 |
| SQLite FTS5 implementation, PostgreSQL stub | overview.md:381-384 | services_review:65-67 |
| Webhook encryption at rest (AES-256-GCM) | overview.md:502 | core_review:109, infrastructure_review:16 |
| Webhook HMAC-SHA256 signing | overview.md:501 | infrastructure_review:12 |
| SSRF protection for webhooks | overview.md:502 | infrastructure_review:13 |
| FTS5 BM25 ranking | overview.md:458 | infrastructure_review:21 |
| "Did you mean?" suggestions via difflib | overview.md:459 | infrastructure_review:26 |
| Search snippet highlighting | overview.md:460 | infrastructure_review:24 |
| Newsletter retry count of 5 | overview.md:430 | tasks_review:44 |
| Preview requires HMAC token AND admin session | overview.md:292 | routes_review:63 |
| Feed endpoints: /atom, /rss, /json | overview.md:348-352 | routes_review:59-61 |
| Vite 6.x with code splitting and `manualChunks` | overview.md:521 | frontend_review:21-22 |
| Context processors (inject_csrf, inject_config, etc.) | overview.md:532 | frontend_review:35-39 |
| Template filters (markdown_safe, reading_time, etc.) | overview.md:533 | frontend_review:28-33 |
| Health check critical checks (database, scheduler, search, disk_space, db_integrity) | overview.md:77 | infrastructure_review:36, deployment_review:22 |
| CSRF sliding window of 5 tokens | overview.md:547 | deployment_review:25 |
| Rate limiting via Flask-Limiter | overview.md:554 | deployment_review:21 |
| Account lockout: 5 failed attempts → 15-minute lockout | overview.md:549 | deployment_review:65 |
| 2FA with TOTP secrets encrypted (AES-256-GCM) | overview.md:545 | core_review:81, deployment_review:24 |
| 8 backup codes, SHA-256 hashed, single-use | overview.md:546 | Verified in models.py |
| Celery tasks retry policies | overview.md:430 | tasks_review:13-19 (all verified) |
| SMTP with TLS and authentication | overview.md:476 | infrastructure_review:28 |
| Local and S3 storage backends | overview.md:483-488 | infrastructure_review:32-33 |

**Total Verified Claims:** 33

---

## 2. Inaccurate/Outdated Claims

| Claim | Overview Location | Issue | Correction |
|-------|-------------------|-------|------------|
| "Retry Policy: max_retries=3 with exponential backoff" | overview.md:430 | Newsletter task has `max_retries=3` but `NEWSLETTER_MAX_RETRY_ATTEMPTS` is 5 for actual newsletter retry count (celery-tasks.md does not document this). APScheduler `send_daily_newsletter` directly calls `send_newsletter()` which uses `NEWSLETTER_MAX_RETRY_ATTEMPTS=5`. | Clarify: email tasks use max_retries=3, but newsletter logic uses NEWSLETTER_MAX_RETRY_ATTEMPTS=5 |
| "Note: There are two backup implementations" - then describes compression/encryption for both | overview.md:369-371 | `run_daily_backup()` in scheduler has NO encryption/compression | Update to clarify: `create_backup()` (Celery) supports compression/encryption; `run_daily_backup()` (APScheduler) does not |
| Queue routing table shows `send_newsletter_task` at `app/tasks.py:130` for webhooks | overview.md:65 | Actually `deliver_webhook_task` is at line 182, `send_newsletter_task` is at line 130 | Line reference is correct for send_newsletter_task, but the overview diagram shows `• newsletter` at line 65 under Celery Worker - this is correct |

---

## 3. Consistency Issues

| Item | Overview | Module Doc | Issue |
|------|----------|------------|-------|
| **Tag Cache Location** | Listed as service at `app/services/tag.py` (overview.md:22, 172) | Tag cache is at `app/tag_cache.py`, NOT in services | services_review:77 - Tag cache file location incorrectly implies it's a service |
| **Search Provider Documentation** | Referenced in Quick Reference (overview.md:21) as `app/services/search/`, overview.md:377-388 | services_review:113 - No document exists for `app/services/search/` module | Overview references `services/overview.md` but search provider is not documented there |
| **Email Task Retry Behavior** | overview.md:427 describes email tasks with max_retries=3 | tasks_review:52-53 - `send_confirmation_task` and `send_password_reset_task` catch exceptions and return False, so max_retries=3 is ineffective (no automatic retry occurs) | Overview should note this is the retry configuration, but actual retry behavior depends on exception handling |
| **Tag Service Path** | overview.md:22, 172 references `app/services/tag.py` | Tag service is correctly at `app/services/tag.py` | Verified correct - no issue |
| **Backup Encryption File Extension** | Overview does not specify extension for encrypted backups | services_review:91 - encrypted files retain `.db` extension (`.gpg` not used) | Overview is silent on extension - consistent with actual behavior |
| **Search Provider in Services Overview** | overview.md:21 references search but doesn't clarify it has multiple implementations | services_review:123 - `architecture/services/overview.md` doesn't list search provider abstraction properly | services/overview.md needs update |
| **API Rate Limits** | Overview does not mention API rate limits in quick reference | routes_review:62 - API has DEFAULT_LIMIT="20 per minute", WRITE_LIMIT="10 per minute" | Missing from overview's API section |
| **Optional Health Checks** | Health section (overview.md:453-468) doesn't mention optional checks | infrastructure_review:37, 77 - Redis and Celery checks are optional and don't affect overall status | Missing documentation of optional vs critical checks |

**Total Consistency Issues:** 8

---

## 4. Recommended Improvements

### High Priority

1. **Clarify APScheduler `send_daily_newsletter` is not a Celery task** (overview.md:441)
   - Currently documented under "Task Processing" with Celery tasks
   - Actually calls `send_newsletter()` synchronously (tasks_review:41)
   - Move to separate section or clarify it bypasses Celery

2. **Fix Search Provider Documentation Gap** (overview.md:21, 377-388)
   - Overview references `app/services/search/` and `services/overview.md`
   - services/overview.md does not document the search provider abstraction
   - Create documentation for `SearchProvider`, `SQLiteSearchProvider`, `PostgreSQLSearchProvider`

3. **Document Two Backup Implementation Differences Explicitly** (overview.md:369-371)
   - `create_backup()` in Celery supports compression/encryption
   - `run_daily_backup()` in APScheduler does NOT
   - Current note is insufficient; add table comparing both

### Medium Priority

4. **Add API Rate Limits to Overview** (overview.md:326-344)
   - Add "Rate Limits: 20/min read, 10/min write" to API Routes section
   - Reference routes_review:62 for evidence

5. **Document Tag Cache Location Correctly** (overview.md:172)
   - Tag cache is at `app/tag_cache.py`, not `app/services/tag_cache.py`
   - Current overview doesn't mention tag_cache.py at all
   - Add to directory structure under `app/` root, not services

6. **Clarify Newsletter Retry Configuration** (overview.md:430)
   - "max_retries=3" applies to Celery task wrapper
   - Actual newsletter retry count is `NEWSLETTER_MAX_RETRY_ATTEMPTS=5`
   - Add note explaining the two retry mechanisms

7. **Add Optional Health Checks Documentation** (overview.md:453-468)
   - Document that Redis and Celery checks are optional
   - They appear in detailed output but don't affect overall status
   - Reference infrastructure_review:36-37

### Low Priority

8. **Document APScheduler Daemon Mode** (overview.md:435-449)
   - scheduler.md doesn't document `daemon=True` (tasks_review:69)
   - Overview should note scheduler runs as daemon thread

9. **Add Multi-Container Deployment Reference** (overview.md:446)
   - Multi-worker FileLock limitation should reference DEPLOY.md
   - Current reference to scheduler.md is insufficient (tasks_review:70)

10. **Document `send_daily_newsletter` SMTP_HOST Condition** (overview.md:441)
    - Job only runs if SMTP_HOST is configured (tasks_review:33)
    - Not mentioned in overview

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 33 |
| Inaccurate/Outdated Claims | 3 |
| Consistency Issues | 8 |
| Recommended Improvements | 10 |

---

## Key Findings

### Strengths

The overview.md is largely accurate and provides a solid high-level view of the architecture. Key strengths include:

1. **Correct architecture diagram** - Celery queues, APScheduler jobs, and database schema are accurately represented
2. **Accurate technology stack** - All technologies and versions match (Flask 3.1+, Vite 6.x, etc.)
3. **Security features correctly documented** - 2FA, webhook encryption, CSRF, rate limiting all verified
4. **Directory structure mostly accurate** - Only minor issues with tag_cache location

### Critical Discrepancies

1. **Search Provider Documentation Gap** - The overview references search abstraction but no module documentation exists
2. **Two Backup Implementations Not Clearly Distinguished** - Overview implies both have encryption/compression but scheduler version does not
3. **APScheduler Newsletter Job Misrepresented** - Documented under Celery but actually runs synchronously via APScheduler

### High-Value Corrections

The most impactful improvements would be:
1. Creating search provider documentation to fill the referenced but non-existent doc
2. Clarifying the two backup implementation differences
3. Separating APScheduler's `send_daily_newsletter` from Celery task documentation