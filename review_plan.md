# Architecture Review Plan

Review each architecture module by having subagents verify document claims against actual code, identify bugs, and propose improvements.

## Modules and Subagents

| Module | Docs | Subagent Task |
|--------|------|---------------|
| [Core](core/) | app-factory.md, models.md, configuration.md | Review core app architecture |
| [Routes](routes/) | admin-routes.md, public-routes.md, api-routes.md, rss-feeds.md | Review route handlers |
| [Services](services/) | backup.md, slug.md, serialization.md, tag.md | Review service layer |
| [Tasks](tasks/) | celery-tasks.md, scheduler.md | Review background task system |
| [Infrastructure](infrastructure/) | email.md, search.md, storage.md, webhooks.md | Review infrastructure services |
| [Frontend](frontend/) | templates.md, static-assets.md | Review frontend architecture |
| [Deployment](deployment/) | docker.md, cicd.md, security.md, overview.md | Review deployment setup |
| [Testing](testing/) | test-suite.md | Review testing infrastructure |

## Review Instructions for Subagents

Each subagent will:
1. Read all documents in their designated module
2. Identify claims and assertions in the documents
3. Locate relevant source code files
4. Verify each claim against the actual implementation
5. Identify discrepancies, bugs, or outdated information
6. Propose code improvements
7. Write findings to `plans/{module}_review.md`

## Execution

```bash
# Launch all module reviews in parallel via Task tool
```

## Output

Each subagent writes an improvement plan to `plans/{module}_review.md` containing:
- Verified claims
- Discrepancies found
- Bugs identified
- Improvement recommendations
- Priority (high/medium/low)

---

## Completed Implementation (May 2026)

### Critical Bugs Fixed

| Item | Priority | Status | Details |
|------|----------|--------|---------|
| S3 image variant upload overwrites original | Critical | ✅ Done | `app/tasks.py:106` - removed premature storage.save() |
| Missing /rss endpoint (RSS 2.0) | Critical | ✅ Done | `app/routes/rss.py` - added rss_feed() |
| Missing /json endpoint (JSON Feed) | Critical | ✅ Done | `app/routes/rss.py` - added json_feed() |
| Webhook events never triggered | Critical | ✅ Done | Added create_webhook_event() calls for post.published, post.unpublished, subscriber.confirmed |

### High Priority Fixes

| Item | Priority | Status | Details |
|------|----------|--------|---------|
| Celery worker PYTHONPATH issue | High | ✅ Done | `docker-compose.yml` - added PYTHONPATH=/home/blog |
| nginx.conf user directive (blog → nginx) | High | ✅ Done | `nginx/nginx.conf:1` |
| Backup encryption documentation (GPG → AES-256-GCM) | High | ✅ Done | `architecture/deployment/security.md:55` |
| critical.css missing | High | ✅ Done | Created `app/static/css/critical.css` |
| AGENTS.override.md filter list incorrect | High | ✅ Done | Fixed `app/templates/AGENTS.override.md` |
| Page view buffer in E2E tests | High | ✅ Done | Added ensure_buffer_disabled to `tests/e2e/conftest.py` |
| Page view buffer in benchmarks | High | ✅ Done | Added ensure_buffer_disabled to `tests/benchmarks/conftest.py` |
| Page view buffer in test_api | High | ✅ Done | Added ensure_buffer_disabled to `tests/test_api.py` |

### Deferred/Not Implemented

| Item | Priority | Reason |
|------|----------|--------|
| Move import logic to serialization service | High | Deferred - scope creep, import works via CLI |
| Fix serialization.md documentation | High | Deferred - documentation only, import handled via CLI |

---

## Branch Structure

All fixes applied via separate branches merged to main:
- `fix/tasks-s3-upload-bug` - S3 upload fix
- `fix/routes-rss-json-feeds` - RSS/JSON feed endpoints
- `fix/webhook-events-triggering` - Webhook event triggering
- `fix/deployment-issues` - Deployment fixes + critical.css + AGENTS.override.md
- `fix/testing-page-view-buffer` - Testing buffer fixes

### Notes for Future Agents

1. **Webhook events** - Events are now triggered for:
   - Post publish/unpublish (in `app/routes/api/posts.py`)
   - Subscriber confirmation (in `app/routes/public/subscribe.py`)
   
2. **Feed endpoints** - Three feeds now available:
   - `/atom` - Atom 1.0 feed (existing)
   - `/rss` - RSS 2.0 feed (new)
   - `/json` - JSON Feed 1.1 (new)

3. **Page view buffer** - All test fixtures now properly disable buffer