# Overview Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** `architecture/overview.md`
**Source Files:** Cross-referenced against `app/__init__.py`, `app/config.py`, `app/models.py`, `app/extensions.py`, `app/routes/`, `app/services/`, `app/tasks.py`, `app/scheduler.py`, `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py`, `app/filters.py`, `app/context_processors.py`, `app/vite.py`, `app/routes/public/meta.py`, and all module directories. Phase 1 review findings used as cross-reference context.

## Findings

### Verified Claims (Correct)

- **Deep dive links**: All 27 architecture doc link references are valid (paths exist in `architecture/` directory)
- **Health check location**: `app/routes/public/meta.py` (line 241 of overview) — correct
- **SSRF protection**: "URL validation against private IP ranges" — confirmed in `app/utils.py:383-485` (`is_safe_webhook_url`)
- **Webhook signing**: HMAC-SHA256 with `X-Webhook-Signature` header — confirmed in `app/webhooks.py:32-36` and `app/tasks.py:274`
- **Session fixation**: `session.clear()` before `login_user()` — confirmed in `app/routes/admin/auth.py:70`
- **CSRF sliding window**: 5 valid tokens — confirmed in `app/csrf.py:8`
- **Account lockout**: 5 failed attempts → 15-minute lockout — confirmed in `app/config.py:161-162`
- **Backup codes**: 8 codes — confirmed in `app/models.py:82`
- **APScheduler jobs**: All 4 jobs match source (`app/scheduler.py:292-321`)
- **Celery queues**: All 5 queues match task decorators (`app/tasks.py`)
- **Route directory structure**: All admin, API, public route files and helpers match actual directory contents
- **Services layer**: All 6 service files plus search/ subdirectory match actual structure
- **Search provider abstraction**: 3 files (`__init__.py`, `sqlite.py`, `postgresql.py`) match `app/services/search/`
- **Extension descriptions**: SQLAlchemy, LoginManager, Migrate — confirmed in `app/extensions.py`
- **Template filters**: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub` — confirmed in `app/filters.py`
- **Vite integration**: `app/vite.py` with `vite_asset()` helper — confirmed

### Discrepancies (Doc vs Code)

1. **Model count "20 models" (line 99) and "19 models" (line 312)** — Actual count is 17 models: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken (`app/models.py`)
   - File: `architecture/overview.md:99,312`

2. **`tag_cache.py` location (line 389)** — Directory structure shows `app/services/tag_cache.py` but actual location is `app/tag_cache.py` (top-level, not under services/)
   - File: `architecture/overview.md:389`
   - Actual: `app/tag_cache.py`

3. **`tag_cache.py` double listing** — Listed both at line 326 (`app/tag_cache.py`, correct) and line 389 (`app/services/tag_cache.py`, incorrect)
   - File: `architecture/overview.md:326,389`

4. **`app/cli.py` missing from directory structure** — `app/cli.py` exists (registers CLI commands via `register_cli_commands()` in `app/__init__.py:464-466`) but is not listed in the directory structure section
   - Actual: `app/cli.py`
   - Referenced: `app/__init__.py:464`

5. **`app/validators.py` not in Core component table** — Listed in directory structure (line 314) but absent from the Core Application component table (lines 86-91)
   - File: `architecture/overview.md:86-91`

### Cross-Reference Inconsistencies

1. **Plans directory links reference non-existent files (lines 492-499)** — The Review Plans section links to `plans/core_review.md`, `plans/routes_review.md`, `plans/services_review.md`, `plans/tasks_review.md`, `plans/infrastructure_review.md`, `plans/frontend_review.md`, `plans/deployment_review.md`, `plans/testing_review.md`. None of these files exist yet. The overview is written as if Phase 1 module reviews are already completed.
   - File: `architecture/overview.md:492-499`
   - Existing plans: `plans/plan.md` (completed Wave 1 implementation), `plans/improvements.md`, `plans/AGENTS.override.md`

2. **Health check `?detailed=true` parameter** — No discrepancy in overview (it doesn't reference the query parameter). The actual implementation uses `?detailed=true` (string comparison) in `app/routes/public/meta.py:194`, not `?detailed=1` (numeric). This is consistent with the Phase 1 findings noting `?detailed=true` is correct.

3. **Disk space threshold** — No discrepancy in overview (it doesn't reference the threshold). The actual implementation checks `free_percent >= 10` (10% free) in `app/routes/public/meta.py:235`, not 100MB. Consistent with Phase 1 findings.

### Missing Documentation

1. **`app/cli.py`** — CLI commands module (registers `flask` CLI commands) is not mentioned anywhere in the overview. Referenced by `app/__init__.py:464-466` via `register_cli_commands(app)`. Should appear in the Core section and directory structure.

2. **`app/validators.py`** — API input validation utilities (189 lines) are listed in directory structure but not in the Core section's component table. Contains `validate_string`, `validate_post_input`, `validate_subscriber_input`, etc.

3. **`app/markdown_config.py`** — Markdown processing configuration (referenced by `app/filters.py:8` and `app/routes/rss.py:10`) is listed in directory structure but not described in any module section.

### Potential Bugs / Concerns

1. **Stale directory structure entry** — `app/services/tag_cache.py` (line 389) does not exist. Developers navigating the directory tree to find tag caching code will be directed to the wrong path. The file is at `app/tag_cache.py`.

2. **Plans section creates false expectation** — The Review Plans section (lines 486-499) lists 8 review documents as if they're available, but none exist yet. This could mislead readers into thinking the reviews are complete.

### Improvement Suggestions

1. Fix model count from "20 models" and "19 models" to "17 models" in both locations (lines 99, 312)
2. Remove `app/services/tag_cache.py` from directory structure (line 389) since it's already correctly listed as `app/tag_cache.py` (line 326)
3. Add `app/cli.py` to directory structure and Core section component table
4. Add `app/validators.py` to Core section component table
5. Conditionalize or remove the Review Plans section (lines 486-499) until Phase 1 review files are created, or add a note that these are planned deliverables

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Fix model count: change "20 models" (line 99) and "19 models" (line 312) to "17 models" | `architecture/overview.md:99,312` |
| 2 | high | Remove stale `app/services/tag_cache.py` from directory structure (line 389) | `architecture/overview.md:389` |
| 3 | med | Add `app/cli.py` to directory structure and Core section component table | `architecture/overview.md:86-91,306-333` |
| 4 | med | Add `app/validators.py` to Core section component table | `architecture/overview.md:86-91` |
| 5 | low | Add note to Review Plans section that documents are planned deliverables not yet created | `architecture/overview.md:486-499` |
