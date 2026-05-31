# Architecture Stale Item Pruning

**Reviewed:** 2026-05-31
**Based on:** 9 module review findings (core, routes, services, tasks, infrastructure, frontend, deployment, testing, overview)

---

## Docs to DELETE

None. All architecture docs have source files that still exist and contain significant correct content alongside the discrepancies. No doc has >50% of claims wrong or documents a fully removed feature.

---

## Docs to REWRITE

### 1. `architecture/testing/test-suite.md`

**Rationale:** Contains multiple factually false claims that are actively misleading:
- **Line 190-196:** Claims E2E conftest does NOT define its own `app` fixture — FALSE. `tests/e2e/conftest.py:11-43` defines a session-scoped `app` fixture.
- **Line 190:** Claims running `pytest tests/e2e/` alone fails — OUTDATED. E2E tests are now runnable standalone.
- **Line 113:** Claims playwright is NOT in requirements.txt — FALSE. `playwright>=1.58.0` IS in requirements.txt:18.
- **Line 59:** Claims `mock_render` and `mock_smtp` are autouse — FALSE. They are function-scoped and explicitly requested.
- Omits `FakeSubscriber` dataclass (conftest.py:60-69).
- Registered markers (`slow`, `e2e`) described as functional but never applied to any test.

**Scope:** Full rewrite of E2E section (lines 185-200), correction of playwright claim (line 113), correction of mock_email description (line 59), addition of FakeSubscriber documentation, and update of marker usage status.

### 2. `architecture/routes/public-routes.md`

**Rationale:** Contains phantom routes that do not exist in code:
- **Line 9:** Route table lists `/page/<page>` — NO SUCH ROUTE EXISTS. Home page is `GET /` with `?page=N` query parameter.
- **Lines 18, 24:** Detail sections claim `/page/<int:page>` and `/tag/<slug>/<int:page>` routes exist — NEITHER EXISTS.
- **Line 106:** Claims health check uses `?detailed=1` — actual code checks `?detailed=true` (string, not integer).
- **Lines 72-74:** Short URL redirect documented under "Comment Routes" but implemented in `posts.py`.

**Scope:** Rewrite route table to remove phantom routes, fix health check parameter, relocate short URL documentation.

### 3. `architecture/routes/admin-routes.md`

**Rationale:** Contains wrong route paths and misattributed sections:
- **Line 133:** Claims `POST /admin/users/<id>/password` — actual is `POST /admin/users/password/<id>` (segments swapped).
- **Line 103:** Claims `GET /admin/posts/<id>/revisions/<rev_id>` exists — NO SUCH ROUTE. Only list (`GET /revisions`) and restore (`POST /revisions/<id>/restore`) exist.
- **Lines 143-146:** "Markdown Preview" section placed under "Session Monitoring" heading — actually in `posts/editor.py`.
- Omits `app/routes/admin/helpers/` directory (9 submodules).

**Scope:** Fix route paths, remove phantom revision route, relocate Markdown Preview section, add helpers/ directory.

---

## Docs to MERGE

### 1. `architecture/infrastructure/overview.md` INTO `architecture/overview.md`

**Rationale:** `infrastructure/overview.md` is a thin wrapper that:
- Lists phantom "email" health check (line 34) that doesn't exist in code
- Contains drastically simplified `is_safe_webhook_url()` code snippet (lines 88-98) that misrepresents the ~100-line actual implementation
- Has significant overlap with the main `overview.md`'s Infrastructure section

The main `overview.md` already covers infrastructure components. The sub-module overview adds minimal unique value while introducing errors. Merge the useful unique content (health check details, search provider architecture) into `overview.md` and delete the sub-module file.

### 2. `architecture/services/overview.md` INTO `architecture/services/overview.md` (fix duplicates)

**Rationale:** Contains duplicate entries:
- "Encryption" (line 10) and "Encryption (TOTP)" (line 16) both point to `app/services/encryption.py` with nearly identical descriptions.
- Should be consolidated to a single entry.

This is a minor fix, not a full merge. Just deduplicate the entries.

---

## Stale Items (Line References)

### `architecture/services/search.md`
- **Line 53:** References `app/search.py:349-351` for case preservation — actual logic is at `app/search.py:342-344` (in `get_did_you_mean()`). Lines 349-351 are `highlight_query()`.

### `architecture/services/tag.md`
- **Line for `get_tag_by_slug()`:** Doc says line 34, actual is line 32 (off by 2)
- **Line for `get_all_tags()`:** Doc says line 41, actual is line 37 (off by 4)
- **Line for `delete_tag_if_unused()`:** Doc says line 58, actual is line 55 (off by 3)
- **Line for `get_tag_post_count()`:** Doc says line 48, actual is line 42 (off by 6)

### `architecture/services/tag_cache.md`
- **Line for `_get_tag_counts_cached()`:** Doc says line 30, actual is line 32 (off by 2)
- **Line for `_get_tag_counts()`:** Doc says line 37, actual is line 39 (off by 2)
- **Line for `_get_tag_counts_uncached()`:** Doc says line 44, actual is line 46 (off by 2)
- **Line for `invalidate_tag_cache()`:** Doc says line 50, actual is line 52 (off by 2)

### `architecture/infrastructure/webhooks.md`
- **Line 200:** References `app/tasks.py:333,354` for email queue tasks — actual lines are `app/tasks.py:344` and `app/tasks.py:365` (off by 11 and 19 lines).

### `architecture/deployment/docker.md`
- **Line 65:** References `docker-compose.yml:58` for celery concurrency — actual is line 66 (off by 8).
- **Line 37:** References `docker-compose.yml:111-129` for backup service — actual is lines 119-137.

### `architecture/core/configuration.md`
- **Line 146:** References `app/config.py:164-171` for ADMIN_RATE_LIMITS — actual is lines 165-172 (off by 1).

### `architecture/frontend/static-assets.md`
- **Line 135:** References `vite.config.js:31-39` for JSX support — actual is lines 36-44.

---

## Phantom Claims (Features Described But Not Implemented)

| Doc | Claim | Reality |
|-----|-------|---------|
| `services/search.md:30-33` | "Fallback: LIKE-based search when FTS unavailable" | `search()` returns empty list when FTS unavailable |
| `services/search.md:26-27` | PostgreSQL "falls back to SQLite" | `PostgreSQLSearchProvider` raises `ConfigurationError` on all methods |
| `infrastructure/email.md:84-86` | "Exponential backoff" in retry logic | No sleep/delay between retries; immediate retry loop |
| `infrastructure/overview.md:34` | "email" optional health check | No SMTP connectivity check exists in `app/routes/public/meta.py` |
| `infrastructure/storage.md:73` | All "S3 methods return False or empty lists on failure" | `S3StorageBackend.save()` has no try/except and raises on failure |
| `deployment/docker.md:205-208` | "email" health check listed | No such check exists in health endpoint |
| `deployment/docker.md:301` | "No warning is logged" on encryption failure | Two warnings are logged (backup.py:69-70, 107-110) |
| `services/backup.md:96` | Encryption key from `config.toml [backup]` section | Key loaded ONLY from `BACKUP_ENCRYPTION_KEY` env var |
| `routes/api-routes.md:291` | Returns 503 when API_KEY unset | Returns 401 in all auth failure cases |
| `routes/api-routes.md:309` | "API key check: 1000/hour" rate limit | No such rate limit exists |
| `core/configuration.md:141` | LOGIN_FAILURE_DELAY "no minimum enforced" | Minimum of 0.1 seconds enforced (config.py:148) |

---

## Summary

| Action | Count | Files |
|--------|-------|-------|
| DELETE | 0 | — |
| REWRITE | 3 | testing/test-suite.md, routes/public-routes.md, routes/admin-routes.md |
| MERGE/FIX | 2 | infrastructure/overview.md, services/overview.md |
| Stale line refs | 8 docs | search.md, tag.md, tag_cache.md, webhooks.md, docker.md, configuration.md, static-assets.md, configuration.md |
| Phantom claims | 11 | Across search.md, email.md, overview.md, storage.md, docker.md, backup.md, api-routes.md, configuration.md |
