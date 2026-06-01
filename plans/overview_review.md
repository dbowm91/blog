# Overview Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md
**Cross-Referenced Against:** core_review.md, routes_review.md, services_review.md, tasks_review.md, infrastructure_review.md, frontend_review.md, deployment_review.md, testing_review.md

## Findings

### Verified Claims (Correct)

1. **Model count = 17** (overview.md:16, 106) — Confirmed by core_review.md:44. All 17 models listed correctly: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken.

2. **Queue count = 5** (overview.md:55-60) — Confirmed by tasks_review.md:13. Queues: images, newsletter, webhooks, email, backup.

3. **Scheduled job count = 4** (overview.md:229-232) — Confirmed by tasks_review.md:14. Jobs: send_daily_newsletter, cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup.

4. **Newsletter retry count = 5** (overview.md:238) — Confirmed by tasks_review.md:15 and infrastructure_review.md:21.

5. **Newsletter delivery dual paths** (overview.md:234-237) — Confirmed by tasks_review.md. Scheduler path checks `NEWSLETTER_MAX_RETRY_ATTEMPTS`; Celery task does not.

6. **APScheduler FileLock multi-container warning** (overview.md:240) — Confirmed by tasks_review.md:22 and deployment_review.md:20.

7. **Webhook two-level dispatch** (overview.md implied by Celery queue listing) — Confirmed by infrastructure_review.md:16.

8. **FTS5 init failure silent** (overview.md:261) — Confirmed by core_review.md:25 and infrastructure_review.md:12.

9. **All 8 modules present in overview** — Core, Data Models, Routes, Services, Task Processing, Infrastructure, Frontend, Security, Deployment all have sections.

10. **Directory structure** (overview.md:374-501) — Matches actual project layout. Key files like `app/__init__.py`, `app/config.py`, `app/models.py`, `app/routes/`, `app/services/`, `app/tasks.py`, `app/scheduler.py` all at correct paths.

11. **System architecture diagram** (overview.md:29-78) — Correctly shows Nginx → Granian → Celery/Redis/SQLite flow with all 5 queues listed.

12. **Database schema diagram** (overview.md:507-553) — Correctly shows relationships between models including PostSeries junction, Comment self-referential, and Webhook→WebhookEvent.

13. **Key Technologies table** (overview.md:557-579) — All technologies match requirements.txt and actual usage confirmed across module reviews.

14. **Docker Compose requires explicit profiles** (overview.md:364) — Confirmed by deployment_review.md:11.

15. **Health check endpoint exists** (overview.md:263-285) — Confirmed by infrastructure_review.md:44 (though the review notes the endpoint is undocumented in infrastructure sub-docs).

### Discrepancies (Doc vs Code)

1. **overview.md:37 — Nginx proxy_pass address**
   - Doc says "Static Files, Load Balancing, Brotli" but doesn't specify proxy_pass address.
   - deployment_review.md:30-33 notes `docker.md:298` incorrectly claims `proxy_pass http://127.0.0.1:5000`, while actual code is `proxy_pass http://blog:5000`.
   - **Severity**: Low for overview.md (omission), High for docker.md (wrong address).

2. **overview.md:175 — Backup encryption module location**
   - Doc lists `app/backup_encryption.py` as a separate file in the Services Layer table.
   - This is correct per services_review.md:53, but overview.md doesn't clarify the relationship between `app/services/encryption.py` (TOTP secrets) and `app/backup_encryption.py` (backup file encryption). The distinction is unclear to readers.

3. **overview.md:18 — Tag cache service listing**
   - Services table lists 7 services but omits `app/services/tag_cache.md` deep dive link while including it in the deep dive column.
   - The `tag_cache.md` deep dive link is present at overview.md:18 but the Service source column doesn't list `app/tag_cache.py` (it's listed in Core Application at line 98).
   - **Severity**: Low — `tag_cache.py` is correctly listed under Core (line 98) but could confuse readers looking in Services.

4. **overview.md:332-351 — Security section incomplete**
   - Security architecture section lists features but omits several cross-cutting concerns identified in module reviews:
     - CSRF applied to ALL POST requests including API (core_review.md:134) — could break API-only clients
     - Comment rate limiting uses `X-Forwarded-For` without proxy validation (core_review.md:144, routes_review.md:64)
     - Token enumeration timing protection (routes_review.md:45)
     - Admin session IP binding enforce/warn modes (routes_review.md:59)
   - **Severity**: Medium — readers get incomplete security picture.

5. **overview.md:22 — Security deep dive reference**
   - Points to `deployment/security.md` but the security module is listed as separate from deployment in the module table (module #8 vs #9).
   - The module table creates confusion: Security is listed as module 8 but has no dedicated deep dive column entry — it shares `deployment/security.md` with Deployment.
   - **Severity**: Low — structural inconsistency.

6. **overview.md:217-224 — Queue listing missing backup queue tasks**
   - The Celery Queues table lists 5 queues with task descriptions, but the `backup` queue just says "Database backups" without noting it's invoked via `run_backup_task` → `run_daily_backup` from scheduler.
   - This cross-module dependency (Scheduler → Celery task) is implied but not explicit.
   - **Severity**: Low.

7. **overview.md:72-75 — Database table listing includes `post_tags`**
   - The ASCII diagram shows `post_tags` as a junction table but it's not listed in the model count (17 models, correct).
   - However, `post_tags` is not documented anywhere in the Models section or as a model — it's an association table defined implicitly by SQLAlchemy's `db.Table`.
   - **Severity**: Low — technically correct but could confuse readers looking for the `PostTag` model.

8. **overview.md:297-308 — SSRF protection location mismatch**
   - Doc says SSRF protection is at `app/webhooks.py` but the actual implementation is at `app/utils.py:383-485`.
   - The `app/webhooks.py` file calls `is_safe_webhook_url()` but doesn't define it.
   - infrastructure_review.md:8 confirms `is_safe_webhook_url()` is at `app/utils.py:383-485`.
   - **Severity**: Medium — misdirects readers to wrong file.

### Missing Documentation

1. **Cross-module dependency: Scheduler → Celery tasks**
   - overview.md:234-237 describes two newsletter delivery paths but doesn't explain the general pattern: APScheduler jobs call Celery tasks via `.delay()` for async execution.
   - This pattern applies to backup (`run_daily_backup` → `run_backup_task`) and is critical for understanding the architecture.
   - **Source**: overview.md:215-242.

2. **CSRF scope not clarified**
   - overview.md:341 mentions CSRF "globally enforced via `before_request_handler()`" but doesn't specify it applies to ALL POST requests including API endpoints.
   - core_review.md:134 identifies this as a potential concern for API-only clients using Bearer tokens.
   - **Source**: overview.md:341.

3. **Error handler routes undocumented**
   - overview.md:146 lists `app/routes/errors.py` with purpose "404, 500, 413 responses" but no detail.
   - routes_review.md:40 notes no architecture doc covers error handling behavior.
   - **Source**: overview.md:146.

4. **Rate limiting overview missing**
   - overview.md:348 mentions "Rate Limiting" as a security feature but provides no summary of limits.
   - routes_review.md:20 confirms rate limits across admin (5/min login, 5/min 2FA, 5/min forgot-password), public (60/min browse, 20/min search, 30/min archive, 10/min subscribe, dual-key comments), and API (20/min read, 10/min write).
   - **Source**: overview.md:348.

5. **RSS/Feed caching behavior undocumented**
   - overview.md doesn't mention ETag/conditional GET (304) support for feeds.
   - routes_review.md:39 notes all feed endpoints implement `If-None-Match` / `304 Not Modified`.
   - **Source**: overview.md:145.

6. **Search fallback behavior undocumented**
   - overview.md:198-202 describes FTS functions but doesn't mention fallback to ILIKE when FTS returns no results.
   - routes_review.md:52 notes browse.py:290-308 falls back to ILIKE.
   - **Source**: overview.md:198-202.

7. **`app/validators.py` location mismatch in directory tree**
   - overview.md:382 shows `app/validators.py` as a top-level file.
   - overview.md:97 correctly lists it under Core Application.
   - No discrepancy, but the validators module isn't referenced in any other module review, suggesting limited usage.

8. **`app/page_view_buffer.py` not mentioned in any module section**
   - overview.md:393 lists it in directory structure but it's not discussed in any module section (Core, Infrastructure, or Services).
   - It's referenced in overview.md:28 as "Page view buffer initialization" but its mechanics (daemon thread, configurable buffer size) aren't explained.
   - **Source**: overview.md:28, 393.

9. **`app/markdown_config.py` and `app/transaction.py` not discussed**
   - overview.md:398-399 lists these in the directory structure but no module section explains their purpose.
   - **Source**: overview.md:398-399.

10. **`app/base62.py` not discussed**
    - overview.md:401 lists it but no module section explains its use for post ID encoding.
    - **Source**: overview.md:401.

11. **`app/csv_utils.py` not discussed**
    - overview.md:400 lists it but no module section explains CSV export utilities.
    - **Source**: overview.md:400.

12. **`app/backup_integrity.py` not discussed**
    - overview.md:395 lists it but no module section explains backup verification.
    - **Source**: overview.md:395.

### Potential Bugs / Concerns

1. **SSRF protection misattributed** (overview.md:299-308)
   - overview.md:299 says "SSRF Protection (`app/webhooks.py`)" but the `is_safe_webhook_url()` function is at `app/utils.py:383-485`.
   - `app/webhooks.py` imports and calls this function but doesn't define it.
   - **Impact**: Developers modifying SSRF protection will edit the wrong file.
   - **Fix**: Change source reference to `app/utils.py`.

2. **CSRF enforcement scope undocumented** (overview.md:341)
   - overview.md:341 says CSRF "globally enforced via `before_request_handler()`" without noting it applies to all POST requests including API endpoints.
   - core_review.md:134 identifies that API clients using `ApiToken` (Bearer token) don't have a Flask session with CSRF tokens, so POST requests would get 403.
   - **Impact**: API integrators may be surprised by CSRF blocking.
   - **Fix**: Document that CSRF applies to all POSTs and note the interaction with API authentication.

3. **Template inheritance hierarchy wrong** (overview.md implied)
   - overview.md doesn't explicitly state template inheritance, but the directory structure at overview.md:404-449 implies a hierarchy.
   - frontend_review.md:39-41 confirms `admin/base.html` and `admin/login_base.html` are standalone, NOT extending `base.html`.
   - **Impact**: Developers modifying templates may assume inheritance that doesn't exist.
   - **Fix**: Add note in Frontend section that admin templates are standalone.

4. **`marked.min.js` loading method wrong** (overview.md implied by Vite discussion)
   - overview.md:326 warns about Vite build requirement for production.
   - frontend_review.md:43 confirms `marked.min.js` is loaded via `vite_asset()`, not `url_for('static', ...)` as some docs claim.
   - **Impact**: Confusion about which assets go through Vite pipeline.
   - **Fix**: Ensure overview.md Frontend section notes all JS assets use `vite_asset()`.

5. **Celery SMTP_HOST missing in docker-compose** (overview.md:364 deployment context)
   - overview.md:364 notes Docker Compose profiles but doesn't list required environment variables.
   - deployment_review.md:40-43 notes `docker-compose.yml` celery service omits `SMTP_HOST` while including `SMTP_USER` and `SMTP_PASSWORD`.
   - **Impact**: Celery worker may fail on newsletter tasks in production if `SMTP_HOST` not set.
   - **Fix**: Add SMTP_HOST to celery service environment.

6. **Post.published NULL allowing not mentioned** (overview.md:112-113)
   - overview.md:112 describes Post as "Blog posts with revisions, tags, series" without noting the `published` column allows NULL.
   - core_review.md:130 identifies this as a potential bug where posts could become invisible.
   - **Impact**: Data integrity issue not surfaced in architecture docs.
   - **Fix**: Note in Data Models section that Post.published and Page.published lack `nullable=False`.

7. **Health check optional checks not emphasized** (overview.md:277-284)
   - overview.md:277-284 lists optional checks (backup_freshness, redis, celery) but doesn't clarify they're only available with `?detailed=true&secret=<key>`.
   - infrastructure_review.md:44 notes the endpoint supports authenticated detailed results.
   - **Impact**: Operations team may not know how to access detailed health info.
   - **Fix**: Note authentication requirement for detailed health check.

8. **`_invalidate_all_caches()` dead code not mentioned** (overview.md:170 services context)
   - overview.md describes Services Layer but doesn't mention cache invalidation patterns.
   - services_review.md:61 identifies `_invalidate_all_caches()` as dead code — defined but never called.
   - **Impact**: Readers may assume coordinated cache invalidation exists when it doesn't.
   - **Fix**: Note actual cache invalidation pattern (per-function calls in route handlers).

### Improvement Suggestions

1. **Add cross-module dependency diagram** — overview.md should include a diagram showing how modules interact: Scheduler → Celery tasks → Email/Webhooks/Backup, Routes → Services → Infrastructure, etc. Currently each module is described in isolation.

2. **Add required environment variables summary** — overview.md should list critical env vars (SECRET_KEY, ADMIN_PASSWORD, SMTP_HOST, REDIS_URL, HEALTH_CHECK_SECRET) with their purposes. Currently scattered across config.md and deployment docs.

3. **Document CSRF scope for API clients** — Add a note in Security section clarifying that CSRF applies to all POST requests and that API clients using Bearer tokens need to handle this (either by using GET-only endpoints or by disabling CSRF for API routes).

4. **Fix SSRF source file reference** — Change overview.md:299 from `app/webhooks.py` to `app/utils.py` to match actual implementation location.

5. **Add rate limiting summary table** — Create a compact table in Security or Routes section showing rate limits for all endpoint categories (admin login, 2FA, public browse, search, subscribe, comment, API read/write).

6. **Document search fallback behavior** — Add a note in Infrastructure/Search section that FTS falls back to ILIKE when no FTS results are found, and that "did you mean" suggestions are provided.

7. **Document RSS caching (ETag/304)** — Add note in Routes/Feeds section that all feed endpoints support conditional GET for efficient caching.

8. **Add `app/page_view_buffer.py` to module table** — Either add it to Infrastructure section or note it in Core Application with its daemon thread and configurable buffer size mechanics.

9. **Document admin template independence** — Add note in Frontend section that `admin/base.html` and `admin/login_base.html` are standalone templates, not extending `base.html`. This is a critical architectural detail for template maintenance.

10. **Add Post.published nullable warning** — Note in Data Models section that `Post.published` and `Page.published` columns allow NULL despite documented intent of `nullable=False`. Reference core_review.md action item #1.

11. **Document health check authentication** — Expand health check section to note that `?detailed=true` requires `?secret=<HEALTH_CHECK_SECRET>` parameter.

12. **Add `SMTP_HOST` to celery service** — Fix docker-compose.yml to include `SMTP_HOST` in celery service environment variables.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | High | Fix SSRF source file reference from `app/webhooks.py` to `app/utils.py` in overview.md:299 | architecture/overview.md |
| 2 | High | Document CSRF scope (all POSTs) and API client interaction in Security section | architecture/overview.md |
| 3 | High | Add `SMTP_HOST` to celery service environment variables | docker-compose.yml |
| 4 | Medium | Add cross-module dependency diagram showing Scheduler→Celery, Routes→Services→Infrastructure interactions | architecture/overview.md |
| 5 | Medium | Add rate limiting summary table covering all endpoint categories | architecture/overview.md |
| 6 | Medium | Document admin template independence (standalone, not extending base.html) | architecture/overview.md |
| 7 | Medium | Document search fallback to ILIKE and "did you mean" feature | architecture/overview.md |
| 8 | Medium | Document RSS ETag/conditional GET (304) caching support | architecture/overview.md |
| 9 | Medium | Note Post.published and Page.published nullable issue (NULL-allowing columns) | architecture/overview.md |
| 10 | Medium | Document health check authentication requirement for detailed results | architecture/overview.md |
| 11 | Low | Add required environment variables summary (SECRET_KEY, ADMIN_PASSWORD, SMTP_HOST, REDIS_URL) | architecture/overview.md |
| 12 | Low | Document `app/page_view_buffer.py` daemon thread and buffer mechanics | architecture/overview.md |
| 13 | Low | Document `marked.min.js` uses `vite_asset()` (not `url_for`) in Frontend section | architecture/overview.md |
| 14 | Low | Add `app/backup_integrity.py`, `app/base62.py`, `app/csv_utils.py`, `app/markdown_config.py`, `app/transaction.py` purpose descriptions to directory structure | architecture/overview.md |
| 15 | Low | Fix Security module (#8) deep dive reference to not share `deployment/security.md` with Deployment (#9) | architecture/overview.md |
| 16 | Low | Note that `_invalidate_all_caches()` is dead code; actual invalidation is per-function in route handlers | architecture/overview.md |
