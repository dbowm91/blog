# Architecture Stale Item Pruning

**Created:** 2026-05-31
**Based on:** 9 module review files in `plans/*_review.md`

## Summary

After cross-referencing all 33 architecture docs against actual codebase implementation, no documents qualify for outright deletion. However, 6 documents have significant discrepancies requiring rewrite, and 3 documents have minor issues requiring targeted fixes.

---

## Docs to REWRITE (Major Discrepancies)

### 1. `architecture/frontend/templates.md`
**Rationale:** Contains 2 HIGH-priority factual errors about template inheritance.
- **Error 1:** Claims `admin/base.html` extends `base.html` (line 71). Reality: `admin/base.html` is standalone with `<!DOCTYPE html>` at line 1.
- **Error 2:** Claims `admin/login_base.html` extends `base.html` (line 73). Reality: Also standalone with `<!DOCTYPE html>` at line 1.
- **Impact:** Developers modifying templates will assume inheritance that doesn't exist, leading to broken changes.
- **Scope:** Rewrite Template Inheritance section to accurately document 3 standalone base templates. Add note about triple duplication maintenance risk.

### 2. `architecture/frontend/static-assets.md`
**Rationale:** Contains 1 HIGH-priority factual error about JS loading and misleading Prism claims.
- **Error 1:** Claims `marked.min.js` is loaded outside Vite via `url_for('static', ...)` (lines 135-139). Reality: Both `base.html:150` and `admin/base.html:162` use `vite_asset('js/lib/marked.min.js')`.
- **Error 2:** Claims Prism.js is lazy-loaded by `main.js` only when code blocks are present (line 213). Reality: `login_base.html:56-57` loads Prism eagerly via `<script defer>`.
- **Impact:** Confusion about which assets go through Vite pipeline; incorrect assumptions about Prism loading.
- **Scope:** Rewrite JS Asset Loading section to correctly describe `vite_asset()` usage. Add note about login page Prism bypass.

### 3. `architecture/deployment/docker.md`
**Rationale:** Contains 1 HIGH-priority factual error about nginx proxy_pass.
- **Error 1:** Claims `proxy_pass http://127.0.0.1:5000` (line 298). Reality: `nginx/conf.d/blog.conf:52` uses `proxy_pass http://blog:5000`.
- **Error 2:** Backup service line range wrong (claims 119-137, actual is 119-139).
- **Impact:** Developers configuring nginx will use wrong address; Docker networking won't work with 127.0.0.1.
- **Scope:** Fix proxy_pass address to use Docker service name `blog`. Correct backup service line range.

### 4. `architecture/services/encryption.md`
**Rationale:** Contains 1 MEDIUM-priority error about function names.
- **Error:** Claims functions are named `encrypt_secret()` and `decrypt_secret()` (line 17). Reality: Actual names are `encrypt()` and `decrypt()` at `app/services/encryption.py:41,69`.
- **Impact:** Developers calling these functions will get ImportError/AttributeError.
- **Scope:** Fix function name references throughout the document.

### 5. `architecture/overview.md`
**Rationale:** Contains 1 MEDIUM-priority SSRF misattribution and incomplete security section.
- **Error 1:** Claims SSRF protection is at `app/webhooks.py` (line 299). Reality: `is_safe_webhook_url()` is at `app/utils.py:383-485`.
- **Error 2:** Security section (lines 332-351) omits CSRF scope (all POSTs including API), X-Forwarded-For trust assumption, token enumeration timing protection, admin session IP binding modes.
- **Impact:** Developers modifying SSRF protection will edit wrong file; readers get incomplete security picture.
- **Scope:** Fix SSRF source reference. Expand Security section with cross-cutting concerns from module reviews.

### 6. `architecture/testing/test-suite.md`
**Rationale:** Contains 2 MEDIUM-priority documentation gaps.
- **Error 1:** Missing `api_client` and `mock_email` fixtures from fixture table.
- **Error 2:** `clean_analytics_cache` source attributed to `conftest.py` (line 42) but actually in `shared_fixtures.py:17-24`.
- **Error 3:** Test file count inflated to "~36" (actual ~30).
- **Impact:** Developers looking for fixtures won't find them in docs.
- **Scope:** Add missing fixtures to table. Fix source attribution. Correct test file count.

---

## Docs to FIX (Minor Discrepancies)

### 7. `architecture/routes/rss-feeds.md`
**Rationale:** 1 line number error.
- **Error:** Cache-Control header reference says `rss.py:98` (line 236). Actual location: `rss.py:90`.
- **Scope:** Fix line number reference.

### 8. `architecture/services/tag_cache.md`
**Rationale:** 2 stale line number references.
- **Error 1:** `editor.py:89,204` should be `77,192` (line 31).
- **Error 2:** `manage.py:82` should be `70` (line 33).
- **Scope:** Update line numbers.

### 9. `architecture/tasks/scheduler.md`
**Rationale:** Stale line numbers and misleading wording.
- **Error 1:** Line references for task file are off by ~1 (line 64-68).
- **Error 2:** "inline `run_daily_backup()` service function" (line 53) is misleading — it imports from `app.services.backup`.
- **Scope:** Fix line numbers and wording.

---

## Docs with Missing Sections (No Rewrite Needed)

These docs are largely correct but have documented gaps. They should be extended rather than rewritten:

| Doc | Missing Content |
|-----|-----------------|
| `architecture/core/app-factory.md` | `inject_show_footer_posts()` context processor, OpenAPI YAML route, `config.toml` requirement |
| `architecture/core/configuration.md` | `APP_TITLE`, `APP_DESCRIPTION`, `AUTHOR_AVATAR`, `CDN_URL` env var, `CSRF_ENABLED`, `RATE_LIMIT_STORAGE_URI` production default |
| `architecture/core/models.md` | Detailed sections for Subscriber, Tag, PageView, ShareEvent |
| `architecture/routes/admin-routes.md` | Admin login rate limiting, 2FA rate limiting, session IP binding, syntax themes |
| `architecture/routes/api-routes.md` | Composed decorator pattern (`@require_api_key` + `@require_scope`) |
| `architecture/routes/public-routes.md` | Error handlers, token enumeration protection, search fallback, "did you mean", series feed ordering |
| `architecture/infrastructure/` | Missing `overview.md` entirely; health check endpoint undocumented |
| `architecture/services/search.md` | `init_fts()` function missing from function table |
| `architecture/deployment/docker.md` | Celery `SMTP_HOST` requirement, `BACKUP_DIR` env var, Docker Compose v2.20+ requirement |

---

## Stale Items (Lines Referencing Removed/Incorrect Files/Functions)

| Doc | Line | Issue |
|-----|------|-------|
| `architecture/services/encryption.md:17` | `encrypt_secret()`/`decrypt_secret()` | Function names don't exist; actual: `encrypt()`/`decrypt()` |
| `architecture/deployment/docker.md:298` | `proxy_pass http://127.0.0.1:5000` | Wrong address; actual: `http://blog:5000` |
| `architecture/frontend/static-assets.md:135-139` | `marked.min.js` via `url_for('static', ...)` | Wrong loading method; actual: `vite_asset()` |
| `architecture/frontend/templates.md:71,73` | `admin/base.html` extends `base.html` | Wrong inheritance; actual: standalone |
| `architecture/overview.md:299` | SSRF at `app/webhooks.py` | Wrong file; actual: `app/utils.py` |
| `architecture/routes/rss-feeds.md:236` | `rss.py:98` | Wrong line; actual: `rss.py:90` |
| `architecture/services/tag_cache.md:31,33` | `editor.py:89,204`, `manage.py:82` | Stale line numbers |
| `architecture/tasks/scheduler.md:53` | "inline `run_daily_backup()`" | Misleading; it imports from `app.services.backup` |
| `architecture/tasks/scheduler.md:64-68` | Task file line references | Off by ~1 |
| `architecture/testing/test-suite.md:42` | `clean_analytics_cache` in `conftest.py` | Wrong file; actual: `shared_fixtures.py` |
| `architecture/testing/test-suite.md` | "~36 test files" | Inflated; actual: ~30 |

---

## Action Items

| # | Priority | Description | Doc | Type |
|---|----------|-------------|-----|------|
| 1 | High | Rewrite template inheritance section (3 standalone bases) | `frontend/templates.md` | REWRITE |
| 2 | High | Fix marked.min.js and Prism loading claims | `frontend/static-assets.md` | REWRITE |
| 3 | High | Fix nginx proxy_pass to use `blog` service name | `deployment/docker.md` | REWRITE |
| 4 | Medium | Fix function names (encrypt/decrypt not encrypt_secret/decrypt_secret) | `services/encryption.md` | REWRITE |
| 5 | Medium | Fix SSRF source reference and expand Security section | `overview.md` | REWRITE |
| 6 | Medium | Add missing fixtures, fix source attribution, correct count | `testing/test-suite.md` | REWRITE |
| 7 | Low | Fix Cache-Control line number (98 → 90) | `routes/rss-feeds.md` | FIX |
| 8 | Low | Fix stale line numbers in tag_cache.md | `services/tag_cache.md` | FIX |
| 9 | Low | Fix stale line numbers and "inline" wording | `tasks/scheduler.md` | FIX |

---

## Notes

- No architecture docs are candidates for deletion — all contain unique, mostly-correct content.
- No docs are duplicates of each other.
- The most critical issues are in `frontend/templates.md` and `frontend/static-assets.md` where fundamental architectural assumptions (template inheritance, asset pipeline) are documented incorrectly.
- The `overview.md` SSRF misattribution could send developers to the wrong file when debugging security issues.
- All 8 module review files and 1 overview review file in `plans/` are valid deliverables and should be preserved.
