# Core Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** app-factory.md, configuration.md, models.md
**Source Files:** app/__init__.py, app/config.py, app/models.py, app/extensions.py, app/filters.py, app/context_processors.py

## Findings

### Verified Claims (Correct)

- `create_app()` validates SECRET_KEY (set + min 32 chars), ADMIN_PASSWORD, and calls `_validate_config()` — `app/__init__.py:151-166`
- Flask app created with `instance_relative_config=True` — `app/__init__.py:168`
- `SESSION_COOKIE_SECURE` defaults to "true" string, parsed to bool — `app/__init__.py:180-182`
- `SESSION_COOKIE_SAMESITE` = "Lax" — `app/__init__.py:183`
- `MAX_CONTENT_LENGTH` = `MAX_UPLOAD_SIZE + 1024 * 1024` (1MB headroom) — `app/__init__.py:179`
- SQLite pragmas set via `@event.listens_for(db.engine, "connect")` — `app/__init__.py:249-254`
- WAL journal mode and busy_timeout=5000 — `app/__init__.py:252-253`
- Auto-create first admin user if none exists — `app/__init__.py:397-414`
- Initialize SiteSettings if none exist — `app/__init__.py:417-428`
- Initialize FTS5 search tables — `app/__init__.py:430-433`
- Run integrity check (`PRAGMA integrity_check`) — `app/__init__.py:437-453`
- APScheduler initialization — `app/__init__.py:455-457`
- Page view buffer initialization — `app/__init__.py:459-462`
- Before request: request ID, CSP nonce, CSRF validation, session timeout — `app/__init__.py:289-331`
- After request: security headers, CSP, HSTS, Prometheus — `app/__init__.py:333-386`
- CSP headers match doc exactly — `app/__init__.py:347-357`
- All blueprint registrations verified — `app/__init__.py:266-277`
- Context processors: `inject_csrf`, `inject_config`, `inject_theme`, `inject_footer_data`, `inject_show_footer_posts` — `app/context_processors.py:126-183`
- Template variables `site_title`, `site_description` (not `site_name`/`site_tagline`) — `app/context_processors.py:144-145`
- Extensions: db, login_manager, migrate — `app/extensions.py:5-10`
- `login_manager.login_view = "admin.login"`, `session_protection = "strong"` — `app/extensions.py:7,9`
- Config priority: env vars > config.toml > defaults — `app/config.py:65-70,73-86`
- All config variables in configuration.md Key Settings tables exist in source — `app/config.py`
- `_validate_config()` validates send_time, posts_per_page, confirmation_expiry_hours, smtp_port, base_url — `app/config.py:177-260`
- All model fields, relationships, and indexes documented in models.md match source — `app/models.py`
- `User.__repr__` returns `<User id={self.id}>` (PII-safe) — `app/models.py:125-126`
- `Webhook.secret` property decrypts via AES-256-GCM — `app/models.py:496-516`
- `SiteSettings.get_instance()` singleton pattern — `app/models.py:353-360`
- Post relationships (tags, page_views, share_events, revisions, series_entries, comments) all verified — `app/models.py:202-217`
- Comment self-referential relationship (parent/replies) — `app/models.py:609-610`
- PostSeries unique constraint `uq_series_post` — `app/models.py:587`
- All Post indexes match documentation — `app/models.py:219-226`
- All PageView, ShareEvent, Subscriber, Comment, PostSeries, PostRevision, AdminAuditLog indexes match — verified in source

### Discrepancies (Doc vs Code)

1. **app-factory.md Extensions table missing Flask-Login** — `app/extensions.py:6` defines `login_manager = LoginManager()` and it's initialized at `app/__init__.py:256`. The extensions table only lists SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress but doesn't explicitly call out Flask-Login as a separate initialized extension (it's implied but the init_app call is at line 256, not grouped with others).

2. **app-factory.md:40 rss blueprint prefix is misleading** — Doc says prefix is `/rss`, `/atom`, `/json`. The rss blueprint is defined without `url_prefix` (`app/routes/rss.py:18`), and routes are registered at `/rss`, `/atom`, `/json` directly. The doc implies these are sub-paths under a prefix, but they're top-level routes.

3. **app-factory.md:133 missing `canonical_url` context variable** — `app/context_processors.py:151` provides `canonical_url` but it's not listed in the Context Processors section.

4. **configuration.md:139 MAX_FAILED_ATTEMPTS missing env var column** — Doc shows no env var, but code at `app/config.py:161` reads from config only (correct). However, the table is inconsistent with other security settings that do show env vars.

5. **configuration.md:140 LOCKOUT_DURATION_MINUTES missing env var column** — Same as above, `app/config.py:162`.

6. **models.md missing `ApiToken` model entirely** — `app/models.py:623-655` defines ApiToken with fields (id, name, token_hash, scopes, created_at, last_used_at, expires_at, revoked_at) and methods (is_valid, has_scope). Not documented anywhere.

7. **models.md:14 User model missing `nullable` constraints** — Doc shows `db.Column(db.String(80), unique=True)` but source has `nullable=False` on username (`app/models.py:25`), and `nullable=True` on email (`app/models.py:26`).

8. **models.md:14 User.email nullable mismatch** — Doc implies email is required (listed without nullable note), but source has `nullable=True` (`app/models.py:26`).

9. **models.md:127 Post model missing `created_at` and `updated_at`** — Source has both (`app/models.py:190-195`), doc omits them.

10. **models.md Comment model missing `is_spam`, `spam_score`, `created_at` fields** — Source has `is_spam` (bool, default=False), `spam_score` (Float, nullable), `created_at` (UTCDateTime) at `app/models.py:604-606`. None documented.

11. **models.md:99 Comment index table missing `ix_comments_is_spam`** — Source has this index at `app/models.py:616`.

12. **models.md SiteSettings missing `updated_at` field** — Source has `updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)` at `app/models.py:351`.

13. **models.md Page model missing `created_at` and `updated_at`** — Source has both at `app/models.py:160-165`.

14. **models.md PostRevision missing `created_at` field** — Source has it at `app/models.py:250`.

15. **models.md AdminSession missing `ix_admin_sessions_user_id` index** — Source defines it at `app/models.py:336`.

16. **configuration.md missing `ADMIN_RATE_LIMITS`** — `app/config.py:164-171` defines admin rate limit tuples (login, api_write, api_read, settings, post_create, post_update). Not documented.

17. **configuration.md missing comment-related settings** — `APP_TITLE`, `APP_DESCRIPTION`, `COMMENT_MIN_LENGTH`, `COMMENT_MAX_LENGTH`, `COMMENT_RATE_LIMIT_PER_IP`, `COMMENT_RATE_LIMIT_PER_POST`, `COMMENT_NOTIFY_PENDING`, `COMMENT_SPAM_WORDS` exist in config.py (lines 137-142) but aren't documented.

18. **configuration.md missing `ANALYTICS_DAYS_MIN` and `ANALYTICS_DAYS_MAX`** — `app/config.py:129-130`.

19. **configuration.md missing `PAGE_VIEW_BUFFER_SIZE`** — `app/config.py:131-133`.

### Missing Documentation

1. **Vite integration** — `app/__init__.py:468-470` calls `init_vite(app)` but app-factory.md doesn't mention it.
2. **CLI commands** — `app/__init__.py:464-466` calls `register_cli_commands(app)` but not documented.
3. **Structured logging** — `app/__init__.py:79-148` implements JSON structured logging with request ID filter. Not documented.
4. **ProxyFix middleware** — `app/__init__.py:185-186` applies `ProxyFix` with configurable `PROXY_COUNT`. Not documented.
5. **`SESSION_COOKIE_HTTPONLY`** — `app/__init__.py:184` sets this to True. Not documented.
6. **Prometheus metrics** — `app/__init__.py:59-74` initializes optional Prometheus counters/histograms. Mentioned briefly in after_request but not in extensions or setup docs.
7. **`CSRF_ENABLED` config** — `app/__init__.py:189` checks for this config key. Not in configuration.md.
8. **Database engine pool options** — `app/__init__.py:202-213` configures pool_size, max_overflow, pool_recycle, pool_pre_ping, pool_timeout for non-SQLite databases.
9. **`db.select()` vs `db.session.query()`** — The codebase consistently uses SQLAlchemy 2.0 `db.session.execute(select(...))` pattern but this convention isn't documented in app-factory.md.
10. **`openapi.yaml` route** — `app/__init__.py:279-281` serves OpenAPI spec at `/openapi.yaml`. Not documented.
11. **`sqlite3` datetime adapter registration** — `app/__init__.py:40-42` registers adapters for Python 3.12+ compatibility.
12. **Error handler for 429** — `app/__init__.py:239-245` handles rate limit errors. Not documented.
13. **Shell context processor** — `app/__init__.py:472-497` registers models for Flask shell.
14. **Cache configuration** — Production uses RedisCache, dev uses SimpleCache (`app/__init__.py:221-233`). Not documented.
15. **`RATELIMIT_HEADERS_ENABLED`** — Set to False at `app/__init__.py:218`. Not documented.

### Potential Bugs / Concerns

1. **`_validate_config()` is called before Flask app config is fully populated** — `app/__init__.py:164-166` imports `_validate_config` and `_raw_config` and calls `_validate_config(_raw_config)`. The raw config dict is validated, not the final app.config. This is correct behavior but worth noting that env-var-overridden values aren't validated.

2. **User model `email` field is `nullable=True`** — `app/models.py:26`. The User model allows null emails, but the architecture doc doesn't call this out. If email is intended for password reset flows, null emails could cause issues.

3. **Comment model `author_name` is `nullable=False`** — `app/models.py:600`. The doc shows `author_name = db.Column(db.String(100))` without noting the constraint.

4. **`load_user` uses `db.session.get()`** — `app/models.py:131`. This is SQLAlchemy 2.0 style but could raise issues if `user_id` isn't a valid integer (ValueError not caught).

5. **RSS feed dead code** — `app/routes/rss.py:201,306,354,459,640` have expressions like `utc_now().isoformat() + "Z"` that compute a value but don't assign or use it. These appear to be leftover debugging or incomplete refactoring.

6. **Configuration validation doesn't check `LOCKOUT_DURATION_MINUTES` or `MAX_FAILED_ATTEMPTS`** — `app/config.py:177-260`. These security settings have no validation bounds.

### Improvement Suggestions

1. Document `ApiToken` model in models.md — it's a first-class model with its own table and methods.
2. Add `canonical_url` to the context processors list in app-factory.md.
3. Document the `created_at`/`updated_at` fields on all models that have them (Post, Page, Comment, PostRevision, SiteSettings).
4. Add `is_spam` and `spam_score` fields to Comment model documentation.
5. Document `ADMIN_RATE_LIMITS` in configuration.md.
6. Add comment-related settings (`COMMENT_MIN_LENGTH`, etc.) to configuration.md.
7. Document Vite integration and CLI commands in app-factory.md.
8. Fix the rss blueprint prefix documentation — clarify routes are at root level, not under a prefix.
9. Add `nullable` constraints to model field documentation where non-default.
10. Remove or annotate dead code in RSS feed functions (unused `utc_now().isoformat()` expressions).

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Add `ApiToken` model to models.md Model Overview and details section | models.md |
| 2 | high | Add `is_spam`, `spam_score`, `created_at` fields to Comment model docs | models.md |
| 3 | high | Add `ix_comments_is_spam` index to Comment index table | models.md |
| 4 | high | Add `canonical_url` to context processors list | app-factory.md |
| 5 | med | Document `created_at`/`updated_at` on Post, Page, Comment, PostRevision, SiteSettings | models.md |
| 6 | med | Fix rss blueprint prefix description (routes are top-level, not prefixed) | app-factory.md |
| 7 | med | Add `ADMIN_RATE_LIMITS` to configuration.md | configuration.md |
| 8 | med | Add comment settings (min/max length, rate limits, spam words) to configuration.md | configuration.md |
| 9 | med | Add `ANALYTICS_DAYS_MIN/MAX`, `PAGE_VIEW_BUFFER_SIZE` to configuration.md | configuration.md |
| 10 | med | Document `ix_admin_sessions_user_id` index in AdminSession section | models.md |
| 11 | low | Document Vite integration and CLI commands in app-factory.md | app-factory.md |
| 12 | low | Add `nullable` constraints to User model field docs (email nullable=True) | models.md |
| 13 | low | Document structured logging, ProxyFix, and cache configuration | app-factory.md |
| 14 | low | Investigate dead code in RSS feed functions (unused expressions) | N/A (code) |
