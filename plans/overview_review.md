# Overview Cross-Reference Review

**Reviewed:** 2026-05-31
**Architecture Doc:** architecture/overview.md
**Module Reviews Cross-Referenced:** core, routes, services, tasks, infrastructure, frontend, deployment, testing

## Findings

### Verified Claims (Correct)

- **17 model classes** (overview.md:106) -- Confirmed by core_review.md:29 ("All 17 model classes present in app/models.py") and source verification (17 `class.*db.Model` definitions, 17 `__tablename__` entries).
- **5 Celery queues** (overview.md:215-222) -- `images`, `newsletter`, `webhooks`, `email`, `backup` all confirmed by tasks_review.md:11 and infrastructure_review.md:52-54.
- **4 APScheduler jobs** (overview.md:224-230) -- All 4 jobs and schedules confirmed by tasks_review.md:16.
- **Model names and descriptions** (overview.md:110-128) -- All 17 models listed with accurate descriptions, confirmed by core_review.md:29-38.
- **Routes layer structure** (overview.md:140-147) -- Public, Admin, API, RSS/Feeds, Error Handlers all confirmed by routes_review.md.
- **API routes match** (overview.md:152-163) -- All endpoints and files confirmed by routes_review.md:20.
- **Services layer structure** (overview.md:166-179) -- Backup, Encryption, Search, Slug, Tag, Serialization all confirmed by services_review.md:10.
- **Search provider abstraction** (overview.md:185-201) -- SearchProvider ABC, SQLiteSearchProvider, PostgreSQLSearchProvider stub all confirmed by infrastructure_review.md:24-26 and services_review.md:22-24.
- **Newsletter two-path delivery** (overview.md:232-234) -- Scheduled (APScheduler) and manual (Celery) paths confirmed by tasks_review.md:19.
- **Silent FTS initialization** (overview.md:255) -- `app/__init__.py:430-433` catches OperationalError silently, confirmed by infrastructure_review.md:63 and core_review.md:18.
- **Security features list** (overview.md:278-299) -- Authentication, 2FA, Backup Codes, CSRF, API Auth, Account Lockout, SSRF Protection, Webhook Signing, XSS, Audit Logging, Rate Limiting, Session Fixation all confirmed across deployment_review.md and core_review.md.
- **Docker multi-stage build** (overview.md:310-311) -- Confirmed by deployment_review.md:12.
- **CI workflow structure** (overview.md:314) -- 6 jobs and weekly schedule confirmed by deployment_review.md:24-25.
- **Key Technologies** (overview.md:500-522) -- Flask 3.1+, SQLAlchemy 2.0, Granian, Celery 5.x, APScheduler, Vite 6.x all confirmed across multiple reviews.
- **Vite build requirement** (overview.md:274) -- Warning about manifest.json and production deployment confirmed by frontend_review.md.
- **FTS5 functions** (overview.md:195-200) -- `init_fts()`, `sync_fts()`/`sync_fts_batch()`, `search()`, `get_search_snippets()`, `get_did_you_mean()` all confirmed by infrastructure_review.md:19-22,27.
- **CSRF sliding window** (overview.md:289) -- 5 valid tokens per session confirmed by core_review.md:102 and deployment_review.md:30.
- **Account lockout** (overview.md:291) -- 5 failed attempts, 15-minute lockout confirmed by deployment_review.md:31.
- **Backup encryption** (overview.md:292) -- AES-256-GCM with PBKDF2 confirmed by deployment_review.md:32 and services_review.md:16-18.
- **Webhook encryption** (overview.md:293) -- AES-256-GCM with HMAC-SHA256 signing confirmed by deployment_review.md:33 and infrastructure_review.md:42,49.
- **Directory structure** (overview.md:320-449) -- File paths and organization match actual codebase structure.

### Discrepancies (Doc vs Module Reviews)

1. **Database tables list missing `api_tokens`** (overview.md:72-76) -- The system architecture diagram lists 16 tables but there are 17 models. The `api_tokens` table is missing from the tables list. Source: `app/models.py:626` defines `__tablename__ = "api_tokens"`.
   - **Affects:** overview.md, source code understanding

2. **Database schema diagram missing ApiToken** (overview.md:453-496) -- The ER diagram does not include the ApiToken model at all. This is a significant omission since ApiToken is the foundation of the scoped API authentication system.
   - **Affects:** overview.md

3. **Newsletter "Three-Way Path" but two paths described** (overview.md:232) -- The heading says "Newsletter Three-Way Path" but the text immediately says "two delivery paths" and only describes two paths (scheduled and manual). This is an internal inconsistency. The same issue exists in `architecture/tasks/celery-tasks.md:48`.
   - **Affects:** overview.md, celery-tasks.md

4. **API Auth oversimplified** (overview.md:290) -- Describes API authentication as "X-API-Key header with HMAC timing-safe comparison" (single mechanism). Routes_review.md:58-59 reveals a two-tier system: (1) legacy `API_KEY` environment variable via `_verify_api_key()`, and (2) scoped `ApiToken` model via `_verify_token()` with hash-based lookup, `is_valid()` check, and `last_used_at` tracking. The overview omits the entire ApiToken-based system.
   - **Affects:** overview.md

5. **Services table missing encryption modules** (overview.md:166-179) -- `app/webhook_encryption.py` and `app/backup_encryption.py` are important encryption modules listed in the directory structure (lines 344-345) but absent from the Services Layer table. Meanwhile, `architecture/services/overview.md:17-18` includes them.
   - **Affects:** overview.md

6. **Core Application source list incomplete** (overview.md:85) -- The "Source:" line lists 6 files (`__init__.py`, `config.py`, `extensions.py`, `filters.py`, `context_processors.py`, `tag_cache.py`) but the component table (lines 89-98) also includes `app/cli.py` and `app/validators.py`, which are not in the source list.
   - **Affects:** overview.md

7. **Deployment section missing Docker Compose profiles** (overview.md:303-316) -- The deployment section does not mention that all services require explicit profiles (`production`, `backup`) with no default profile. Deployment_review.md:13 confirms this is a critical deployment detail.
   - **Affects:** overview.md

8. **Deployment section missing Granian ASGI details** (overview.md:303-316) -- The architecture diagram (line 43) shows "Granian ASGI Server (Rust)" but the deployment section table only mentions "Docker" generically. The Granian server is a key production component not reflected in the deployment documentation.
   - **Affects:** overview.md

9. **FTS key functions list incomplete** (overview.md:195-200) -- Lists 5 functions but infrastructure_review.md:22 and services_review.md:89-90 note that `rebuild_fts()`, `extract_snippet()`, `get_indexed_terms()`, `_escape_fts_term()`, and `_check_fts_enabled()` are also important public/utility functions not listed.
   - **Affects:** overview.md

10. **Infrastructure health check missing actual checks** (overview.md:253) -- Lists "Health Check | app/routes/public/meta.py | System health monitoring" but does not enumerate the actual checks performed. The infrastructure/overview.md lists them but incorrectly includes an "email" check (line 34) that does not exist in `app/routes/public/meta.py:200-287`. Actual checks are: database, scheduler, search, disk_space, db_integrity (critical), redis, celery, backup_freshness (optional).
    - **Affects:** overview.md, infrastructure/overview.md

11. **Newsletter retry count not stated** (overview.md:204-236) -- The Task Processing section does not mention the retry count. Tasks_review.md:24 confirms `NEWSLETTER_MAX_RETRY_ATTEMPTS` defaults to 5. AGENTS.md also documents this as "default is 5 (not 3 as some documentation may claim)."
    - **Affects:** overview.md

12. **APScheduler multi-container limitation not mentioned** (overview.md:204-236) -- The Task Processing section does not discuss the FileLock `timeout=0` limitation that causes duplicate job execution in multi-container deployments. AGENTS.md documents this as an important deployment consideration.
    - **Affects:** overview.md

13. **`ENABLE_SCHEDULER` dead config not noted** (overview.md) -- `ENABLE_SCHEDULER` is listed in `app/config.py:55` `__all__` but is never read or used anywhere in the codebase. `init_scheduler()` is always called unconditionally from `app/__init__.py:457`. Tasks_review.md:63-64 flags this as dead configuration.
    - **Affects:** overview.md, source code

14. **CSRF global enforcement mechanism not explained** (overview.md:278-299) -- The Security section mentions CSRF but does not explain that CSRF is enforced globally via `before_request_handler()` in `app/__init__.py:296-298`, which validates CSRF tokens on every POST request automatically. Core_review.md:102 and routes_review.md:68 both flag this as a critical architectural detail.
    - **Affects:** overview.md

15. **Scoped API Token system undocumented** (overview.md:290) -- Overview mentions only legacy API_KEY mechanism. Routes_review.md:72 notes that the `ApiToken` model-based authentication, `require_scope()` decorator, and the full scope list (`posts:read`, `posts:write`, `media:read`, `media:write`, `subscribers:read`, `subscribers:write`, `newsletter:send`, `analytics:read`, `tags:read`, `tags:write`, `pages:read`, `pages:write`, `series:read`, `series:write`, `admin:*`) are undocumented.
    - **Affects:** overview.md

16. **Security headers CSP inconsistency** (overview.md:294) -- Overview mentions "CSP headers" but does not note that Flask uses nonce-based CSP (`script-src 'self' 'nonce-{nonce}'`) while nginx uses `script-src 'self' 'unsafe-inline'`. Deployment_review.md:79-80 and:117-119 flag this as a security downgrade when nginx overrides Flask headers.
    - **Affects:** overview.md

17. **services/overview.md duplicate entries** (architecture/services/overview.md:10,16) -- The services-level overview lists "Encryption" (line 10) and "Encryption (TOTP)" (line 16) both pointing to `app/services/encryption.py`. Services_review.md:84-86 flags this as a duplicate. The main overview.md does not have this duplication (only one entry).
    - **Affects:** architecture/services/overview.md

18. **infrastructure/overview.md "email" health check is phantom** (architecture/infrastructure/overview.md:34) -- Lists "email | SMTP connectivity (if configured)" as an optional check, but no such check exists in `app/routes/public/meta.py:200-287`. Infrastructure_review.md:68-70 confirms this.
    - **Affects:** architecture/infrastructure/overview.md

19. **infrastructure/overview.md is_safe_webhook_url() code snippet is simplified** (architecture/infrastructure/overview.md:88-98) -- Shows a ~10-line version with basic checks. The actual implementation in `app/utils.py:383-485` is ~100 lines with additional checks for userinfo, loopback hostnames, reserved IPs, multicast, IPv4-mapped IPv6, and cloud metadata endpoints. Infrastructure_review.md:72-74 flags this.
    - **Affects:** architecture/infrastructure/overview.md

### Missing Documentation

1. **Module override convention** -- The AGENTS.override.md system for module-specific agent guidance is not mentioned in overview.md. This is a key architectural pattern for AI agent workflows.

2. **Celery concurrency constraints** -- Overview does not document that `_update_delivery_status()` correctness depends on `--concurrency=1` (tasks_review.md:5,7) or that `worker_prefetch_multiplier=1` is a production requirement (tasks_review.md:10).

3. **Newsletter retry path differences** -- Overview does not document that the Celery `send_newsletter_task` does NOT check `NEWSLETTER_MAX_RETRY_ATTEMPTS` (tasks_review.md:3,8), unlike the scheduler path. This behavioral difference is important for understanding retry semantics.

4. **Webhook delivery status concurrency assumption** -- Overview does not document that delivery status tracking assumes single-concurrency execution (tasks_review.md:5, infrastructure_review.md:158).

5. **Email retry architecture** -- Overview does not document the layered retry system: `_send_email_with_retry` defaults to 3 retries (email.py:111) but newsletter always overrides to 5 (tasks_review.md:2, infrastructure_review.md:29).

6. **Search LIKE fallback does not exist** -- Overview does not claim this, but architecture/services/search.md (referenced by overview) claims "Fallback: LIKE-based search when FTS unavailable" (infrastructure_review.md:84-86). The actual code returns an empty list when FTS is unavailable.

7. **PostgreSQL fallback does not exist** -- architecture/services/search.md claims PostgreSQL "falls back to SQLite" (infrastructure_review.md:88-90), but `PostgreSQLSearchProvider` raises `ConfigurationError` on all methods.

8. **Email exponential backoff does not exist** -- infrastructure_review.md:76-78 documents that `_send_email_with_retry()` claims exponential backoff in both docstring and architecture docs, but retries immediately with no delay.

### Inconsistencies

1. **"Three-Way Path" vs two paths** (overview.md:232, celery-tasks.md:48) -- Both documents use the heading "Newsletter Three-Way Path" but describe only two delivery paths. Either the heading should be "Two-Way Path" or a third path needs to be documented.

2. **Model count vs table count** (overview.md:106 vs 72-76) -- Overview correctly states "17 models" in the Data Models section but the database tables list in the architecture diagram only shows 16 tables (missing `api_tokens`).

3. **Services table inconsistency** -- Main overview.md (lines 172-179) lists 6 services. `architecture/services/overview.md` (lines 8-19) lists 10 entries including duplicates and additional modules. The main overview is cleaner but less complete.

4. **Health check documentation inconsistency** -- overview.md:253 says "System health monitoring." infrastructure/overview.md:34 lists "email" as an optional check. The actual code has no email check. Three documents have three different levels of detail, none fully accurate.

5. **API Auth description inconsistency** -- overview.md:290 describes single mechanism. routes_review.md:58-59 reveals two-tier system. The overview is outdated relative to the actual implementation.

6. **Security headers "both Flask and nginx"** -- deployment_review.md:79-80 documents that Flask and nginx set different CSP policies (nonce-based vs unsafe-inline), contradicting the security.md claim that "Both Flask and nginx set these headers" as if they were identical.

### Improvement Suggestions

1. **Fix "Three-Way Path" heading** -- Change to "Newsletter Delivery Paths" or "Two-Way Path" to match the two paths actually described, in both overview.md and celery-tasks.md.

2. **Add `api_tokens` to database tables list** (overview.md:72-76) -- Add the missing table to the architecture diagram's table list.

3. **Add ApiToken to database schema diagram** (overview.md:453-496) -- Include the ApiToken model with its relationships (e.g., no FK to User, standalone token table).

4. **Expand API Auth description** (overview.md:290) -- Document both the legacy API_KEY mechanism and the scoped ApiToken system, including the scope list and `require_scope()` decorator.

5. **Add encryption modules to Services table** (overview.md:166-179) -- Add `app/backup_encryption.py` (Backup Encryption) and `app/webhook_encryption.py` (Webhook Encryption) entries.

6. **Complete Core Application source list** (overview.md:85) -- Add `app/cli.py` and `app/validators.py` to the "Source:" line.

7. **Add Docker Compose profiles to Deployment section** (overview.md:303-316) -- Document that all services require explicit profiles with no default.

8. **Add Granian ASGI details to Deployment section** (overview.md:303-316) -- Mention the Granian ASGI server as the production application server.

9. **Expand FTS key functions list** (overview.md:195-200) -- Add `rebuild_fts()`, `extract_snippet()`, `get_indexed_terms()`, `_escape_fts_term()`.

10. **Add health check details** (overview.md:253) -- Enumerate the critical and optional checks performed by the health endpoint.

11. **Add newsletter retry count** (overview.md:204-236) -- Document `NEWSLETTER_MAX_RETRY_ATTEMPTS=5` in the Task Processing section.

12. **Add APScheduler multi-container warning** (overview.md:204-236) -- Note the FileLock `timeout=0` limitation and recommend single-container or external scheduler for production.

13. **Document CSRF global enforcement** (overview.md:278-299) -- Explain that CSRF is enforced globally on all POST requests via `before_request_handler()`.

14. **Document scoped API token system** (overview.md:290) -- Add the full ApiToken authentication flow with scope list.

15. **Note CSP policy difference** (overview.md:294) -- Document that nginx overrides Flask's nonce-based CSP with a weaker unsafe-inline policy.

16. **Fix infrastructure/overview.md email health check** (architecture/infrastructure/overview.md:34) -- Remove the phantom "email" check or implement it.

17. **Fix infrastructure/overview.md is_safe_webhook_url() snippet** (architecture/infrastructure/overview.md:88-98) -- Replace simplified version with accurate representation or remove and reference `app/utils.py:383-485`.

18. **Fix services/overview.md duplicate entries** (architecture/services/overview.md:10,16) -- Merge the two "Encryption" rows into one entry.

19. **Remove or implement `ENABLE_SCHEDULER`** (app/config.py:55) -- Either use it to gate `init_scheduler()` or remove from `__all__` to avoid confusion.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Add `api_tokens` to database tables list and ApiToken to schema diagram in overview.md | docs |
| 2 | high | Expand API Auth description to cover two-tier system (legacy API_KEY + scoped ApiToken) | docs |
| 3 | high | Fix "Three-Way Path" heading to match two described paths (overview.md:232, celery-tasks.md:48) | docs |
| 4 | high | Document CSRF global enforcement mechanism via before_request_handler() | docs |
| 5 | high | Fix infrastructure/overview.md:34 -- remove phantom "email" health check or implement it | docs/source |
| 6 | high | Fix infrastructure/overview.md:88-98 -- replace simplified is_safe_webhook_url() with accurate version | docs |
| 7 | med | Add encryption modules (backup_encryption.py, webhook_encryption.py) to overview.md services table | docs |
| 8 | med | Complete Core Application source list with cli.py and validators.py | docs |
| 9 | med | Add Docker Compose profiles requirement to Deployment section | docs |
| 10 | med | Add health check details (critical and optional checks) to overview.md | docs |
| 11 | med | Add APScheduler multi-container limitation warning to Task Processing section | docs |
| 12 | med | Document newsletter retry count (5) and retry path differences between Celery and scheduler | docs |
| 13 | med | Fix services/overview.md duplicate Encryption entries | docs |
| 14 | med | Note CSP policy difference between Flask (nonce-based) and nginx (unsafe-inline) | docs |
| 15 | med | Remove or implement ENABLE_SCHEDULER dead config | docs/source |
| 16 | low | Add Granian ASGI server details to Deployment section | docs |
| 17 | low | Expand FTS key functions list with rebuild_fts, extract_snippet, get_indexed_terms, _escape_fts_term | docs |
| 18 | low | Document Celery concurrency constraints for delivery status tracking correctness | docs |
| 19 | low | Document email retry architecture (3 default vs 5 for newsletter) | docs |
| 20 | low | Fix search.md LIKE fallback and PostgreSQL fallback claims (features do not exist) | docs |
