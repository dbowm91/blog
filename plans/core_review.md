# Core Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** app-factory.md, configuration.md, models.md
**Source Files:** app/__init__.py, app/config.py, app/models.py, app/extensions.py, app/filters.py, app/context_processors.py

## Findings

### Verified Claims (Correct)
- **App Factory pattern**: `create_app()` in `app/__init__.py` correctly implements Flask app factory with all 14 initialization steps documented
- **Config validation**: `SECRET_KEY` (min 32 chars), `ADMIN_PASSWORD` requirement, and `_validate_config()` calls are correctly documented (lines 150-166)
- **Flask app setup**: Instance_relative_config, SECRET_KEY, UPLOAD_FOLDER, SQLALCHEMY_DATABASE_URI, SESSION_COOKIE_SECURE/SAMESITE, MAX_CONTENT_LENGTH all match
- **SQLite pragmas**: WAL mode and busy_timeout via event listener (lines 249-254) correctly documented
- **Blueprints**: All 6 blueprints (public, admin, rss, errors, api, swaggerui) registered correctly
- **Before/After request hooks**: Request ID, CSP nonce, CSRF validation, session timeout, security headers all correctly documented
- **Prometheus metrics**: Latency histogram and request counter correctly implemented (lines 59-74, 373-384)
- **Vite integration**: `init_vite(app)` called correctly (line 470)
- **ProxyFix middleware**: `PROXY_COUNT` environment variable with x_for, x_proto, x_host (line 186) correctly documented
- **Cache configuration**: RedisCache for production, SimpleCache for development with 300s TTL (lines 221-233) correctly documented
- **CSP headers**: Full header string matches code exactly (lines 347-356)
- **Configuration priority**: Env vars > config.toml > defaults (lines 91-92, 96-97, 148-153)
- **All 17 models present**: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken
- **User model fields**: username, email, password_hash, is_admin, reset_token, reset_token_expires_at, failed_login_count, locked_until, totp_secret_encrypted, totp_enabled, backup_codes_hashed all match
- **User.__repr__()**: Returns `<User id={self.id}>` (line 126) - PII-safe as documented
- **User methods**: set_password, check_password, is_locked, record_failed_login, reset_failed_login, generate_backup_codes, verify_backup_code, get_totp_uri all present
- **Webhook secret encryption**: Uses AES-256-GCM via property pattern (lines 496-516)
- **WebhookEvent.delivery_status**: Correctly documented with 'delivered', 'partial_failure', 'failed' values
- **Post model indexes**: All 6 indexes correctly documented (ix_posts_published_created, ix_posts_published_at, ix_posts_newsletter_sent_at, ix_posts_published_updated, ix_posts_published_slug, ix_posts_scheduled_publish_at)
- **AdminAuditLog indexes**: ix_admin_audit_logs_actor_timestamp and ix_admin_audit_logs_action_timestamp correctly documented
- **PostRevision indexes**: ix_post_revisions_post_created and ix_post_revisions_author_id correctly documented
- **Comment indexes**: All 4 (post_approved, created_at, parent_id, is_spam) correctly documented
- **ApiToken model**: is_valid() and has_scope() methods correctly documented, admin:* scope wildcard correctly documented
- **SiteSettings.get_instance()**: Singleton pattern with id=1 correctly documented
- **THEME_PRESETS**: All 4 presets (github-dark, github-light, solarized-dark, monokai) with all color values match
- **Cli commands**: All 7 commands (rebuild-search, cleanup-orphaned-images, create-admin, promote-admin, check-integrity, export-data, import-data, seed) registered via `register_cli_commands()`
- **Background services**: APScheduler (init_scheduler) and page view buffer (init_page_view_buffer) correctly initialized
- **Logging**: StructuredLogFormatter with RotatingFileHandler (10MB, 10 backups) to logs/blog.log correctly documented

### Discrepancies (Doc vs Code)

| File:Line | Documentation Claims | Actual Code |
|-----------|---------------------|-------------|
| `extensions.py:5-9` | Shows `login_manager.login_view = "admin.login"` | `login_manager.login_view = "admin.login"` is in `extensions.py` line 7 - **CORRECT**, but the doc shows this code in the "Extensions" section of app-factory.md as if it's set during app creation |
| `extensions.py:176-177` (doc) | Doc shows extensions defined with login_manager.login_view in code block | Actually, `login_manager.login_view` is set in `extensions.py:7`, not during `create_app()`. The doc's "Extensions" code block is misleading |
| `models.py:202` (Post.tags) | Doc says `tags = db.relationship("Tag", secondary=post_tags)` without lazy parameter | Code: `tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")` - missing `back_populates` in doc |
| `models.py:206-217` (Post relationships) | Doc shows cascade="all,delete-orphan" on some relationships | Code shows cascade specified on page_views, share_events, revisions, series_entries, comments - **CORRECT** |
| `models.py:253-254` (PostRevision.author) | Doc does not specify lazy loading | Code: `author = db.relationship("User", lazy="select")` |
| `models.py:536` (WebhookEvent.webhook) | Doc does not specify lazy loading | Code: `webhook = db.relationship("Webhook", lazy="select")` |
| `models.py:558` (Series.posts) | Doc does not specify lazy loading | Code: `posts = db.relationship("PostSeries", back_populates="series", order_by="PostSeries.order_index")` |
| `models.py:253` (PostRevision.post) | Doc shows `back_populates="revisions"` | Code shows `back_populates="revisions"` - **CORRECT** |
| `app-factory.md:20` | "raises error if explicitly False in production" | Code: Lines 195-198 show it raises `RuntimeError` if `SESSION_COOKIE_SECURE` is False in production - **CORRECT** |
| `app-factory.md:148` (note) | Notes `style-src-attr 'unsafe-inline'` is required for theme system | Code: Line 350 shows `style-src-attr 'unsafe-inline'` - **CORRECT** |
| `context_processors.py` | Doc lists `csrf_token` as a context variable | Code: `inject_csrf()` returns `csrf_token` and `csp_nonce` - **CORRECT** |
| `context_processors.py` | Doc lists 5 context processors: inject_csrf, inject_config, inject_theme, inject_footer_data, inject_show_footer_posts | Code: All 5 present and registered - **CORRECT** |

### Missing Documentation

1. **Lazy loading specifications**: Many relationships use `lazy="select"` but docs don't specify this (Post.tags, PostRevision.author, WebhookEvent.webhook, Series.posts, Comment.replies)

2. **Post.tags back_populates**: The `back_populates="posts"` on the Tag relationship is not documented

3. **FLASK_ENV check for Redis**: The code uses `FLASK_ENV` (line 221) to determine cache type, not `FLASK_ENV=production` as documented in the cache table

4. **RATE_LIMIT_STORAGE_URI defaults**: Documented as `memory://` (dev) but actual default is `redis://localhost:6379/1` when `FLASK_ENV=production` (line 150)

5. **login_manager.login_message**: extensions.py line 8 sets `login_manager.login_message` but docs don't mention this

6. **SESSION_COOKIE_HTTPONLY**: Set at line 184 but not documented

7. **COMPRESS_ALGORITHM**: Hardcoded as `["zstd", "br", "gzip"]` in config.py:157 but not documented in configuration.md

8. **ENABLE_SCHEDULER**: Config option exists (config.py:55) but not documented

9. **MAX_FAILED_ATTEMPTS and LOCKOUT_DURATION_MINUTES**: Security settings exist in config.py:161-162 but not documented in configuration.md

10. **Search provider config**: SEARCH_PROVIDER and SEARCH_CONFIG exist in config.py:173-174 but not documented

11. **Database connection pool settings**: Lines 206-213 set SQLALCHEMY_ENGINE_OPTIONS for non-SQLite databases but not documented

12. **TESTING mode disables limiter**: Line 237 `limiter.enabled = False` not documented

13. **HSTS only in non-debug**: Line 346 `if not current_app.debug` - this conditional behavior not documented

14. **CSP Report-Only header in debug**: Lines 358-369 set CSP-Report-Only in debug mode - not documented

15. **Cache-Control for static files**: Line 371 `if req.path.startswith("/static/")` - not documented

16. **prometheus_client optional import**: Lines 61-74 - conditional import with try/except - not documented

17. **AdminAuditLog details**: target_type, details, ip_address fields not documented

18. **WebhookEvent.target_type**: Documented as "post", "subscriber", etc. but not in model docs

19. **Subscriber.expires_at**: Documented but the `doc=` parameter explanation (removal deadline) not documented

20. **Comment.author_email**: Required field (nullable=False) but docs show it as optional

21. **SHELL_CONTEXT_PROCESSOR**: Lines 472-497 define shell context but not documented

### Potential Bugs / Concerns

1. **Config validation missing fields**: `_validate_config()` does NOT validate `base_url` format properly when `base_url` is empty string (line 252 checks `if base_url:` so empty string passes)

2. **Rate limit header disabled**: `RATELIMIT_HEADERS_ENABLED = False` (line 218) means rate limit info is not exposed to clients - this is intentional but undocumented

3. **sqlite3 datetime adapter registration**: Lines 41-42 register adapters globally at module import time - could affect other sqlite3 usage in the process

4. **FTS initialization error handling**: Lines 430-433 silently catches `OperationalError` and rolls back - if FTS init fails, search won't work but no error is raised to the user

5. **Page view buffer init**: `init_page_view_buffer` at line 462 could fail silently if called before db tables exist

6. **Circular import risk**: The `before_request_handler` (lines 289-331) imports `AdminSession` and `db` inside the function to avoid circular imports - this works but is a code smell

7. **Session IP binding**: The `SESSION_IP_BINDING` config option exists but the actual IP binding enforcement logic appears to be missing from `before_request_handler` - only session timeout is checked

8. **CSRF validation**: `validate_csrf_token()` is called for all POST requests but `CSRF_ENABLED` config check happens AFTER warning is logged (line 189 checks after warning) - could be bypassed if CSRF_ENABLED=False

### Improvement Suggestions

1. **Document lazy loading strategy**: Add `lazy="select"` specifications to relationship documentation

2. **Add missing config options**: ENABLE_SCHEDULER, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES, SEARCH_PROVIDER, COMPRESS_ALGORITHM

3. **Update cache documentation**: Fix `FLASK_ENV=production` condition and `RATE_LIMIT_STORAGE_URI` default values

4. **Document login_manager.login_message**: Minor but should be in context processors or extensions docs

5. **Add SESSION_COOKIE_HTTPONLY to docs**: Security-relevant setting currently undocumented

6. **Clarify IP binding**: Either document that `SESSION_IP_BINDING` is not yet implemented, or verify the implementation exists elsewhere

7. **Add error handling docs**: Document that FTS init and page view buffer can fail silently

8. **Document shell context**: Add `flask shell` context processor to CLI docs or app factory docs

9. **Fix config validation**: `base_url` validation should reject empty strings if `base_url` is required

10. **Update EXTENSIONS.md**: Show that `login_manager.login_view` is set in extensions.py, not during create_app()

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | medium | Add lazy="select" specifications to relationship docs (Post.tags, PostRevision.author, WebhookEvent.webhook, Series.posts) | docs/core/models.md |
| 2 | medium | Document missing config options: ENABLE_SCHEDULER, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES, SEARCH_PROVIDER, COMPRESS_ALGORITHM | docs/core/configuration.md |
| 3 | medium | Fix cache documentation: FLASK_ENV condition and RATE_LIMIT_STORAGE_URI defaults | docs/core/app-factory.md |
| 4 | low | Document SESSION_COOKIE_HTTPONLY, login_manager.login_message, RATELIMIT_HEADERS_ENABLED | docs/core/app-factory.md |
| 5 | low | Add shell context processor to documentation | docs/core/app-factory.md |
| 6 | high | Verify SESSION_IP_BINDING implementation - appears unused in before_request_handler | source (app/__init__.py) |
| 7 | medium | Consider failing loudly if FTS initialization fails (currently silent) | source (app/__init__.py) |
| 8 | low | Document CSRF_ENABLED bypass possibility when explicitly set to False | docs/core/app-factory.md |
