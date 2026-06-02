# Core Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/core/app-factory.md, architecture/core/configuration.md, architecture/core/models.md
**Source Files:** app/__init__.py, app/config.py, app/models.py, app/extensions.py, app/filters.py, app/context_processors.py

## Findings

### Verified Claims (Correct)
- Flask app factory initialization sequence (config validation, extensions, blueprints, hooks)
- SQLite pragma setup via SQLAlchemy event listener at app/__init__.py:249-254
- All 17 model classes present and correctly defined
- Model field names, types, defaults, and relationships match documentation
- All model indexes match documentation (ix_posts_*, ix_pages_*, ix_page_views_*, etc.)
- Config priority: env vars > config.toml > defaults
- Configuration defaults: POSTS_PER_PAGE=10, SESSION_LIFETIME_HOURS=24, MAX_UPLOAD_SIZE=10485760, etc.
- LOGIN_FAILURE_DELAY minimum of 0.1s enforced at config.py:149
- RATE_LIMIT_STORAGE_URI defaults: memory:// (dev), redis://localhost:6379/1 (production)
- Page view buffer initialization and thread mechanics
- CLI commands: rebuild-search, cleanup-orphaned-images, create-admin, promote-admin, check-integrity, export-data, import-data, seed
- APScheduler initialization at app/__init__.py:455-457
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- ProxyFix middleware with PROXY_COUNT env var
- Context processors: inject_csrf, inject_config, inject_theme, inject_footer_data, inject_show_footer_posts
- Tag cache using flask-caching with TAG_CACHE_TTL_SECONDS
- Template filters: markdown_safe, reading_time, sanitize_css, post_image_url, post_image_srcset, post_image_avif_url_stub

### Discrepancies (Doc vs Code)

| # | File | Line | Documentation Claims | Actual Code |
|---|------|------|---------------------|-------------|
| 1 | models.md | 159 | `failed_login_count = db.Column(db.Integer, default=0)` | `failed_login_count = db.Column(db.Integer, default=0, nullable=False)` (models.py:31) |
| 2 | models.md | 411 | `SiteSettings.get_instance()` does `db.session.commit()` | Actual code does `db.session.flush()` (models.py:359) - commit happens later via Flask request lifecycle |
| 3 | models.md | 510-516 | "Known Issues" section claims `Post.published` and `Page.published` allow NULL (unfixed) | Issue was FIXED in Wave 1 items 1.2, 1.3. Code shows `nullable=False` at models.py:196,166. Documentation is OUTDATED. |
| 4 | configuration.md | 134 | RATE_LIMIT_STORAGE_URI default "memory:// (dev)" | Incomplete - doesn't mention production defaults to `redis://localhost:6379/1` when FLASK_ENV=production (config.py:150-153) |
| 5 | app-factory.md | 117 | Tag cache uses `_get_tag_counts()` with `@cache.memoize()` | Actual function is `_get_tag_counts_cached()` with memoize at tag_cache.py:32. `_get_tag_counts()` is a wrapper that calls cached or uncached version (tag_cache.py:39-43) |

### Missing Documentation

1. **APScheduler Multi-Container Limitation**: The architecture docs don't mention that APScheduler with FileLock only works on a single machine. Multiple container replicas will each run their own scheduler and execute jobs concurrently. This is documented in docker-compose.yml and AGENTS.md but not in core architecture docs.

2. **Vite Build Requirement**: No documentation that `npm run build` must be run before production deployment and manifest.json must be present.

3. **Docker Compose Profiles**: No documentation that all services require explicit profiles (--profile production, --profile backup).

4. **CSRF Applies to API**: No documentation that CSRF validation is enforced on ALL POST requests including API endpoints. API clients using ApiToken don't have Flask sessions with CSRF tokens, so POST requests get 403. This is a known design choice in plans/plan.md (Wave 2 item 2.12).

5. **Comment Rate Limit Header Bypass**: No documentation that comment rate limiting uses X-Forwarded-For header, which could be bypassed if behind a trusted proxy that doesn't sanitize this header.

6. **Session IP Binding Location**: Documentation suggests global before_request handler but actual implementation is in `admin_required` decorator at app/routes/admin/__init__.py:25-55.

7. **Silent FTS Initialization**: No user-visible error when FTS init fails silently (app/__init__.py:430-433 catches OperationalError).

8. **SiteSettings.get_instance() Unconditional Flush**: get_instance() does flush() unconditionally which commits any other uncommitted changes in the session as a side effect.

9. **Webhook Delivery Architecture**: No documentation of the two-level dispatch pattern (deliver_webhook_task -> deliver_single_webhook_task).

### Potential Bugs / Concerns

1. **SiteSettings.get_instance() Race Condition** (models.py:354-360): If two requests concurrently check `db.session.get(cls, 1)` when instance is None, both could create and add an instance. The flush() helps but doesn't fully prevent race condition. Consider using `db.session.merge()` or SELECT FOR UPDATE.

2. **SiteSettings.get_instance() Side Effect** (models.py:359): The unconditional `flush()` commits any other uncommitted changes in the session as a side effect. If called within a request that has other pending changes, those get committed unexpectedly.

3. **Tag Cache Memoization Key** (tag_cache.py:32): `_get_tag_counts_cached` is memoized with `timeout=TAG_CACHE_TTL_SECONDS` but memoize uses function arguments as cache key. Since there are no arguments, this works like a singleton with TTL - but if TAG_CACHE_TTL_SECONDS changes at runtime, the cache still uses the old TTL until expiry.

4. **Admin Session Cleanup Error Handling** (app/__init__.py:319-326): If session.delete() fails with IntegrityError/OperationalError, it rolls back and logs a warning, but the user is still logged out via `logout_user()`. This is correct behavior but the error path silently loses the admin session record.

5. **Comment Rate Limit Bypass** (app/routes/public/comments.py:24-32): Uses X-Forwarded-For header without validating trusted proxy chain. If behind a misconfigured proxy, rate limiting can be bypassed by spoofing this header.

6. **Config TOML Required** (app/config.py:77-84): If config.toml is missing, Flask app fails to start with a RuntimeError. However, many config values have environment variable overrides, so the TOML file is not always strictly required for all settings.

### Improvement Suggestions

1. **Update models.md "Known Issues" Section**: Remove or mark as resolved the nullable published columns issue (fixed in Wave 1 items 1.2, 1.3).

2. **Fix failed_login_count Documentation**: Add `nullable=False` to the User model documentation at models.md:159.

3. **Clarify SiteSettings.get_instance()**: Document that it uses flush() not commit(), and that this is intentional to integrate with Flask's request lifecycle.

4. **Document APScheduler Limitations**: Add multi-container warning to architecture documentation.

5. **Add Vite Build Requirement**: Document that production deployment requires `npm run build` first.

6. **Document Docker Profiles**: Add profile requirements to documentation.

7. **Document CSRF on API**: Add note about CSRF applying to all POSTs including API, and the implication for API token auth.

8. **Add Security Considerations Section**: Document the X-Forwarded-For rate limit consideration.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Update models.md "Known Issues" section - nullable published columns issue was fixed in Wave 1 | docs |
| 2 | high | Fix User.failed_login_count documentation missing nullable=False | docs |
| 3 | high | Clarify SiteSettings.get_instance() uses flush() not commit() in docs | docs |
| 4 | med | Add APScheduler multi-container limitation to architecture docs | docs |
| 5 | med | Add Vite build requirement to architecture docs | docs |
| 6 | med | Document CSRF-on-API design decision and API token implications | docs |
| 7 | med | Add Docker Compose profile requirements to documentation | docs |
| 8 | low | Consider adding SELECT FOR UPDATE to SiteSettings.get_instance() to prevent race condition | source |
| 9 | low | Document comment rate limit X-Forwarded-For consideration | docs |
| 10 | low | Clarify RATE_LIMIT_STORAGE_URI production default in configuration.md | docs |
