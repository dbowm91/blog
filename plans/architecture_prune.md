# Architecture Pruning Recommendations

**Generated:** 2026-06-02
**Phase:** Phase 2 (Stale Item Pruning after all module reviews)
**Review Source:** 8 module reviews in `plans/*_review.md`

## Summary

After reviewing all 8 module architecture reviews, the architecture documentation is **mostly accurate** but has several categories of issues requiring attention. **No documents should be deleted** — all map to existing source files and have valuable content. However, **2 documents need targeted rewrites** and several have line number drift requiring refresh.

---

## Prune Candidates Analysis

### 1. Documents to DELETE — None

**Rationale:** All 32 architecture documents (excluding this file and review_plan.md) reference existing source files. No docs reference removed features, non-existent files, or deprecated APIs exclusively. The documentation is substantially accurate despite minor discrepancies.

---

### 2. Documents to REWRITE — 2

#### `architecture/deployment/docker.md`
**Rationale:** Multiple significant discrepancies affecting operator understanding:
- Line 37: Backup service range `docker-compose.yml:119-137` is wrong (should be 120-140)
- Lines 88-90: Description of scaling behavior is confusing and could lead to misconfiguration
- APScheduler multi-container warning (lines 103-151) is verbose but accurate — could be condensed

**Scope:** Fix line number references (lines 37, 67, 190-206), clarify scaling warning language

#### `architecture/deployment/security.md`
**Rationale:** Claims headers exist that are NOT in the actual nginx configuration:
- Lines 54-55 claim `X-Download-Options: noopen` and `X-Permitted-Cross-Domain-Policies: none` are set at `nginx/conf.d/blog.conf:25-32`
- These headers are NOT present in nginx/conf.d/blog.conf:25-32
- This is a factual error that could confuse operators

**Scope:** Either add the missing headers to nginx/conf.d/blog.conf and update line reference, OR remove these headers from security.md

---

### 3. Documents to MERGE — None

**Rationale:** No duplicate documentation found. Each doc has unique content and purpose.

---

## Stale Items (Line Number Drift)

Line number references throughout the documentation have drifted. Instead of listing each one individually (dozens of entries), here is the **scope**:

| Module | Document | # of Line Refs Needing Update | Severity |
|--------|----------|-------------------------------|----------|
| Core | models.md | ~5 | Medium |
| Core | app-factory.md | ~2 | Low |
| Core | configuration.md | ~2 | Low |
| Routes | admin-routes.md | ~3 | Medium |
| Services | tag_cache.md | ~2 | Medium |
| Tasks | celery-tasks.md | ~5 | High |
| Infrastructure | webhooks.md | ~3 | Medium |
| Infrastructure | email.md | ~1 | Low |
| Infrastructure | search.md | ~1 | Low |
| Frontend | static-assets.md | ~4 | Medium |
| Deployment | docker.md | ~8 | High |

**Recommendation:** Use symbolic references (function names, class names) instead of line numbers where possible to reduce future drift.

---

## High-Priority Action Items

### Must Fix (Factual Errors)

| # | Document | Issue | Fix |
|---|----------|-------|-----|
| 1 | `security.md:54-55` | Claims X-Download-Options and X-Permitted-Cross-Domain-Policies headers exist in nginx but they don't | Add headers to nginx/conf.d/blog.conf OR remove from security.md |
| 2 | `docker.md:37` | Backup service line range wrong (119-137 vs 120-140) | Update to 120-140 |
| 3 | `celery-tasks.md:20` | generate_image_variants claims max_retries=3 but has NO retries | Fix decorator documentation |
| 4 | `celery-tasks.md:104` | run_backup_task claims max_retries=2 but has NO retries | Fix decorator documentation |
| 5 | `celery-tasks.md:139` | send_newsletter_task says "no explicit retry" but has dead max_retries=3 | Clarify or remove retry config |

### Should Fix (Significant Drift)

| # | Document | Issue | Fix |
|---|----------|-------|-----|
| 6 | `admin-routes.md:228` | THEME_PRESETS (color schemes) confused with syntax themes (Prism) | Clarify distinction |
| 7 | `webhooks.md:120,122` | deliver_webhook_task/deliver_single_webhook_task line numbers off by 5-6 | Update to 200, 237 |
| 8 | `static-assets.md:131` | Claims prefetch.js uses IntersectionObserver but uses mouseenter | Fix mechanism description |

### Nice to Have (Minor)

| # | Document | Issue | Fix |
|---|----------|-------|-----|
| 9 | `models.md:510-516` | "Known Issues" section describes fixed bugs | Remove or mark as resolved |
| 10 | `models.md:159` | failed_login_count missing nullable=False in docs | Add nullable=False |
| 11 | `frontend_review.md` | Various line references off by 1-2 | Update references |

---

## Verification Notes

All source files referenced in architecture docs exist:
- `app/__init__.py` ✓
- `app/config.py` ✓
- `app/models.py` ✓
- `app/extensions.py` ✓
- `app/filters.py` ✓
- `app/context_processors.py` ✓
- `app/routes/admin/` ✓
- `app/routes/api/` ✓
- `app/routes/public/` ✓
- `app/routes/rss.py` ✓
- `app/routes/errors.py` ✓
- `app/services/` ✓
- `app/tag_cache.py` ✓
- `app/backup_encryption.py` ✓
- `app/webhook_encryption.py` ✓
- `app/tasks.py` ✓
- `app/scheduler.py` ✓
- `app/celery_app.py` ✓
- `app/search.py` ✓
- `app/email.py` ✓
- `app/storage.py` ✓
- `app/webhooks.py` ✓
- `app/utils.py` ✓
- `app/templates/` ✓
- `app/static/` ✓
- `app/vite.py` ✓
- `Dockerfile` ✓
- `docker-compose.yml` ✓
- `nginx/conf.d/blog.conf` ✓
- `.github/workflows/ci.yml` ✓
- `scripts/dev.sh` ✓
- `tests/` ✓
- `tests/conftest.py` ✓
- `tests/e2e/conftest.py` ✓
- `pytest.ini` ✓

---

## Conclusion

The architecture documentation is **70-80% accurate with line number drift**. No documents need deletion. Two documents need targeted rewrites (docker.md, security.md) to fix factual errors. The primary issue is **line number references** that have drifted over time — consider using symbolic references to reduce maintenance burden.

**Recommended Next Steps:**
1. Fix the 2 factual errors (security headers, docker line numbers)
2. Fix the 5 high-priority documentation issues (celery-tasks retry configs)
3. Create a process to update line numbers when code changes
4. Consider adding CI check to verify docs compile/build