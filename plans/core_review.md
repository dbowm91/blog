# Core Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** app-factory.md, configuration.md, models.md
**Source Files:** app/__init__.py, app/config.py, app/models.py, app/extensions.py, app/filters.py, app/context_processors.py

## Findings

### Verified Claims (Correct)

- `create_app()` is the main entry point (`app/__init__.py:150`)
- SECRET_KEY validated to be at least 32 characters (`app/__init__.py:155-158`)
- ADMIN_PASSWORD required (`app/__init__.py:160-162`)
- `_validate_config()` called at startup (`app/__init__.py:164-166`)
- Flask app created with `instance_relative_config=True` (`app/__init__.py:168`)
- `SESSION_COOKIE_SECURE` defaults to "true" string, parsed as boolean (`app/__init__.py:180-182`)
- `SESSION_COOKIE_SAMESITE` = "Lax" (`app/__init__.py:183`)
- `MAX_CONTENT_LENGTH` = `MAX_UPLOAD_SIZE + 1024 * 1024` (`app/__init__.py:179`)
- All 6 extensions confirmed: SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress (`app/extensions.py`, `app/__init__.py:52-57,200,220,234,256-257`)
- All 6 blueprints registered: public, admin, rss, errors, api, swaggerui with correct prefixes (`app/__init__.py:266-277`)
- Before-request handler: request ID generation, CSP nonce, CSRF validation for POST, session timeout check (`app/__init__.py:290-331`)
- After-request handler: security headers, CSP with nonce, HSTS, Prometheus metrics (`app/__init__.py:333-386`)
- CSP header content matches doc exactly (`app/__init__.py:347-357`)
- SQLite pragmas set via `@event.listens_for(db.engine, "connect")` (`app/__init__.py:249-254`)
- FTS init failure caught and rolled back silently (`app/__init__.py:430-433`)
- APScheduler initialization (`app/__init__.py:455-457`)
- Page view buffer initialization (`app/__init__.py:459-462`)
- Tag cache uses `@cache.memoize()` with `TAG_CACHE_TTL_SECONDS` TTL (`app/tag_cache.py:32`)
- Cache: RedisCache in production, SimpleCache in dev; 300s TTL, "blog_" prefix (`app/__init__.py:221-232`)
- ProxyFix with `PROXY_COUNT` env var, default 1 (`app/__init__.py:185-186`)
- CSRF sliding window of 5 tokens (`app/csrf.py:20`, `CSRF_TOKEN_WINDOW_SIZE = 5`)
- CSRF token rotation on validation (`app/csrf.py:53-60`)
- CSRF enforcement in `before_request_handler` (`app/__init__.py:297-298`)
- `StructuredLogFormatter` outputs JSON with timestamp, level, request_id, message (`app/__init__.py:79-118`)
- `RequestIdFilter` injects `g.request_id` into log records (`app/__init__.py:124-132`)
- `RotatingFileHandler` with `backupCount=10` (`app/__init__.py:138-139`)
- Logging only in non-debug/non-testing mode (`app/__init__.py:134`)
- `login_manager.login_view` = "admin.login", `session_protection` = "strong" (`app/extensions.py:7,9`)
- `inject_footer_data` excludes `/admin`, `/api`, `/rss` paths (`app/context_processors.py:161`)
- `inject_show_footer_posts` excludes `/search` and `/tag/` paths (`app/context_processors.py:182-183`)
- Context processors provide all documented variables: csrf_token, csp_nonce, site_title, site_description, author_name, author_role, author_avatar, base_url, current_year, canonical_url, theme_preset, theme_vars, syntax_theme, custom_css_enabled, custom_css, logo_text, theme_presets, recent_posts_footer, recent_posts_sidebar, footer_tags, footer_tag_counts, show_footer_posts (`app/context_processors.py`)
- Vite integration reads `.vite/manifest.json`, falls back to MD5 content-hash query strings, respects `CDN_URL` (`app/vite.py`)
- Login failure delay minimum 0.1s enforced (`app/config.py:147`)
- All 17 models confirmed: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken (`app/models.py`, line-by-line count)
- `User.__repr__` returns `<User id={self.id}>` (not username) for PII safety (`app/models.py:125-126`)
- `User.generate_backup_codes()` returns 8 codes, stores SHA-256 hashes (`app/models.py:77-88`)
- `User.verify_backup_code()` is single-use (`app/models.py:90-100`)
- `Tag.generate_slug`, `Post.generate_slug`, `Page.generate_slug`, `Series.generate_slug` all delegate to `app.utils.generate_slug`
- THEME_PRESETS dict with 4 themes: github-dark, github-light, solarized-dark, monokai (`app/models.py:366-457`)
- `SiteSettings.get_instance()` returns singleton id=1, creating if needed (`app/models.py:353-360`)
- All model indexes match documentation (verified every index in `__table_args__` for each model)
- `ADMIN_RATE_LIMITS` dict with 6 entries, values match doc (`app/config.py:164-171`)
- `PAGE_VIEW_BUFFER_SIZE` env var configurable, default 0 (disabled) (`app/config.py:130-132`)
- `PAGE_VIEW_FLUSH_INTERVAL` default 5 seconds (`app/page_view_buffer.py:30`)
- Page view buffer uses daemon thread (`app/page_view_buffer.py:60`)
- Seed command has `--published/--draft` boolean flag pair (`app/cli.py:267`)
- `COMPRESS_ALGORITHM` = `["zstd", "br", "gzip"]` (`app/config.py:157`)
- `WEBHOOK_TIMEOUT` default 10 (`app/config.py:155`)
- `COMMENT_MIN_LENGTH` default 3, `COMMENT_MAX_LENGTH` default 5000 (`app/config.py:136-137`)
- `SEARCH_PROVIDER` default "sqlite" (`app/config.py:173`)
- `SECRET_KEY` and `ADMIN_PASSWORD` loaded from env vars only, no TOML fallback (`app/config.py:90,96`)
- `Subscriber.token` has UUID default, `Subscriber.expires_at` exists with doc string (`app/models.py:270,273-277`)

### Discrepancies (Doc vs Code)

- **Post.published nullable mismatch**: `app-factory.md:336` / `models.md:336` claims `published = db.Column(db.Boolean, default=False, nullable=False)` but `app/models.py:196` has `published = db.Column(db.Boolean, default=False)` -- missing `nullable=False`. SQLAlchemy Boolean defaults to `nullable=True` when not specified, so the database column allows NULL despite the documented intent.

- **Page.published nullable mismatch**: `models.md:381` claims `published = db.Column(db.Boolean, default=False, nullable=False)` but `app/models.py:166` has `published = db.Column(db.Boolean, default=False)` -- same issue as Post.

- **RotatingFileHandler maxBytes inaccuracy**: `app-factory.md:125` says "10MB max" but `app/__init__.py:139` uses `maxBytes=10240000` which is ~9.77MB (10MB would be 10485760). Minor but technically inaccurate.

- **Admin rate limits line number drift**: `configuration.md:148` references `app/config.py:165-172` but the dict spans lines 164-171. Off by 1 line on each boundary.

- **Validation line number drift** (consistent -1 pattern): `configuration.md:186-194` references `app/config.py:214-230`, `232-241`, `243-250` for validation functions, but the actual code spans `213-229`, `231-240`, `242-249` respectively. All off by exactly 1 line.

- **Tag model missing String length docs**: `models.md` table lists `name, slug` as key fields for Tag without specifying lengths. Code at `app/models.py:138-139` uses `String(50)` for both.

- **Post relationship cascade string format**: `models.md:344-348` uses `"all,delete-orphan"` but `app/models.py:204-216` uses `"all, delete-orphan"` (with space). Functionally equivalent in SQLAlchemy but not an exact match.

- **AdminSession relationship attributes undocumented**: `models.md:172` shows `admin_sessions = db.relationship("AdminSession", back_populates="user")` but `app/models.py:36-41` also specifies `lazy="select"` and `cascade="all,delete-orphan"`.

- **`login_manager.login_message` not documented**: `app/extensions.py:8` sets `login_manager.login_message = "Please log in to access this page."` but neither `app-factory.md` nor any other core doc mentions it.

- **`Subscriber` model lacks detailed section**: Unlike User, AdminSession, Webhook, WebhookEvent, Series, PostSeries, PostRevision, Post, Comment, Page, SiteSettings, and ApiToken -- the Subscriber model has no detailed documentation section in `models.md`. Missing: `expires_at`, `unsubscribed_at`, `created_at` field details.

- **`APP_TITLE`/`APP_DESCRIPTION` not in configuration.md tables**: These are defined at `app/config.py:87-88` and used by context processors, but not listed in any configuration category table in `configuration.md`.

- **`AUTHOR_AVATAR` not in configuration.md tables**: Defined at `app/config.py:104` but not listed in the Author settings category in `configuration.md:28-30`.

- **`CDN_URL` not listed as env-var-configurable in configuration.md**: `app/config.py:107` shows `CDN_URL = _env("CDN_URL", ...)` making it overridable by env var, but the Site settings table in `configuration.md` doesn't list it as having an env var override.

- **`SEARCH_PROVIDER`/`SEARCH_CONFIG` not in `__all__`**: These are defined at `app/config.py:173-174` and used by the app, but not included in the `__all__` list at `app/config.py:6-61`.

### Missing Documentation

- **`inject_show_footer_posts()` context processor**: Entirely undocumented in core architecture docs. Controls `show_footer_posts` variable, excludes `/search` and `/tag/` paths (`app/context_processors.py:180-183`).

- **OpenAPI YAML route**: The app serves an OpenAPI spec at `/openapi.yaml` (`app/__init__.py:279-281`). Not mentioned in any core doc.

- **`SQLALCHEMY_TRACK_MODIFICATIONS = False`**: Set at `app/__init__.py:178` but not documented.

- **`SESSION_COOKIE_HTTPONLY = True`**: Set at `app/__init__.py:184` but not mentioned in docs.

- **Connection pool settings for non-SQLite databases**: `app/__init__.py:202-213` configures `pool_size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True, pool_timeout=30` for non-SQLite databases. Not documented.

- **`CSRF_ENABLED` config option**: `app/__init__.py:189` checks `CSRF_ENABLED` and logs a warning if CSRF is disabled in production. Not documented as a configurable option.

- **Rate limiter disabled in testing**: `app/__init__.py:236-237` disables the limiter when `TESTING` is set. Not documented.

- **Shell context processor**: `app/__init__.py:472-497` registers a shell context with model objects for `flask shell`. Not documented.

- **Prometheus metrics optional import**: `app/__init__.py:61-74` gracefully handles missing `prometheus_client` package. Not documented.

- **`config.toml` required at startup**: `app/config.py:78-82` raises `RuntimeError` if `config.toml` not found. This is a critical startup requirement not explicitly stated in docs.

- **`RATE_LIMIT_STORAGE_URI` production default**: Doc at `configuration.md:134` says "memory:// (dev)" but doesn't state the production default (`redis://localhost:6379/1` per `app/config.py:148-151`).

- **`Subscriber` model detailed documentation**: No detailed model section exists for Subscriber in `models.md`. Missing: field definitions, `expires_at` purpose, `unsubscribed_at` semantics.

- **`Tag` model detailed documentation**: No detailed model section for Tag in `models.md`. Missing: `String(50)` length constraint, `generate_slug` method.

- **`PageView` model detailed documentation**: No detailed model section for PageView in `models.md`.

- **`ShareEvent` model detailed documentation**: No detailed model section for ShareEvent in `models.md`.

- **`Subscriber` relationship to `confirm_subscriber_task`**: The `expires_at` field has a doc string but the cleanup mechanism (APScheduler job) is not cross-referenced.

### Potential Bugs / Concerns

- **Post.published allows NULL in database** (`app/models.py:196`): `published = db.Column(db.Boolean, default=False)` without `nullable=False` means the database column allows NULL. Queries filtering on `Post.published == True` would silently exclude rows where `published` is NULL (neither True nor False). This could cause posts to become invisible if ever inserted with a NULL value. Same concern for `Page.published` (`app/models.py:166`).

- **`SiteSettings.get_instance()` unconditional commit** (`app/models.py:359`): The classmethod does `db.session.commit()` unconditionally when creating a new instance. If called within a session that has other uncommitted changes, those changes are committed as a side effect. This is also duplicated by the initialization logic in `app/__init__.py:417-428` which creates SiteSettings directly (not via `get_instance()`).

- **CSRF validation applied to all POST requests including API** (`app/__init__.py:297-298`): The `before_request_handler` enforces CSRF for ALL POST requests globally, including API endpoints. API clients authenticating with `ApiToken` (Bearer token) do not have a Flask session with CSRF tokens, so `validate_csrf_token()` would fail with 403 on any API POST request. This may be intentional defense-in-depth, but could break API-only clients.

- **`is_locked()` does not reset counter after lockout expiry** (`app/models.py:108-112`): After lockout expires (`utc_now() >= locked_until`), `is_locked()` returns False but `failed_login_count` retains its old value (>= `max_attempts`). A subsequent failed login call to `record_failed_login()` would immediately re-lock the account without reaching the threshold again, since `failed_login_count` was never reset. Only `reset_failed_login()` on successful login resets the counter.

- **`Subscriber.confirmed` allows NULL in database** (`app/models.py:271`): `confirmed = db.Column(db.Boolean, default=False)` without `nullable=False` has the same NULL-allowing issue as Post/Page `published`.

- **`User.failed_login_count` allows NULL** (`app/models.py:31`): `failed_login_count = db.Column(db.Integer, default=0)` without `nullable=False`. The `record_failed_login()` method does `self.failed_login_count += 1` which would fail with a TypeError if the value is NULL (Python `None + 1`).

- **`_get_settings_cache_key()` used as `key_prefix` argument** (`app/context_processors.py:44`): The `@flask_cache.cached(timeout=300, key_prefix=_get_settings_cache_key)` uses a function reference, not a string. While this works with flask-caching, the type annotation `key_prefix` expects `str`, hence the `# type: ignore[arg-type]` comment at line 44.

- **Comment rate limiting uses `X-Forwarded-For` without proxy validation** (`app/routes/public/comments.py:24-32`): The `get_client_ip()` function reads `X-Forwarded-For` header. If an attacker controls this header (no trusted proxy stripping it), rate limiting can be bypassed.

- **`inject_footer_data` guard** (`app/context_processors.py:160`): `path = request.path if request else ""` -- `request` is always available within a request context, making the `if request` guard redundant.

### Improvement Suggestions

- Add `nullable=False` to `Post.published` and `Page.published` columns to match documented intent and prevent NULL-related query issues.

- Add `nullable=False` to `User.failed_login_count` to prevent TypeError on increment when value is NULL from legacy data.

- Document `inject_show_footer_posts()` context processor and its path exclusions in `app-factory.md`.

- Document `OpenAPI YAML` route (`/openapi.yaml`) and Swagger UI integration in `app-factory.md`.

- Add `APP_TITLE`, `APP_DESCRIPTION`, and `AUTHOR_AVATAR` to the Application/Author settings tables in `configuration.md`.

- Document `CDN_URL` as env-var-configurable in the Site settings table in `configuration.md`.

- Add `CSRF_ENABLED` to the Security settings table in `configuration.md`.

- Document that `config.toml` is required at startup and the app will not start without it.

- Add detailed model sections for Subscriber, Tag, PageView, and ShareEvent in `models.md`.

- Clarify `RATE_LIMIT_STORAGE_URI` production default (`redis://localhost:6379/1`) in `configuration.md`.

- Update `RotatingFileHandler` documentation to say "~9.8MB" instead of "10MB" for accuracy.

- Consider documenting the CSRF enforcement scope (all POSTs) and how API endpoints interact with it.

- Fix consistent -1 line number drift in `configuration.md` validation references (lines 186-194).

- Add `SEARCH_PROVIDER` and `SEARCH_CONFIG` to the `__all__` list in `app/config.py` if they are considered public API.

- Consider adding a `Subscriber.__repr__` that includes more useful information (e.g., email or id).

- Consider whether `SiteSettings.get_instance()` should use `db.session.merge()` or check-then-create pattern to avoid unconditional commits interfering with outer transactions.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Add `nullable=False` to `Post.published` and `Page.published` to prevent NULL values that break published-status queries | source (app/models.py) |
| 2 | high | Add `nullable=False` to `User.failed_login_count` to prevent TypeError on `None + 1` from legacy NULL rows | source (app/models.py) |
| 3 | high | Investigate and document CSRF enforcement behavior for API POST endpoints; consider exemptions for token-authenticated requests | source/docs |
| 4 | med | Document `inject_show_footer_posts()` context processor and its path exclusions | docs (app-factory.md) |
| 5 | med | Document `OpenAPI YAML` route and Swagger UI integration | docs (app-factory.md) |
| 6 | med | Add `APP_TITLE`, `APP_DESCRIPTION`, `AUTHOR_AVATAR` to config tables | docs (configuration.md) |
| 7 | med | Document `CDN_URL` env var override in Site settings table | docs (configuration.md) |
| 8 | med | Document `CSRF_ENABLED` config option | docs (configuration.md) |
| 9 | med | Document `config.toml` as required startup file | docs (configuration.md) |
| 10 | med | Fix consistent -1 line number drift in validation references | docs (configuration.md) |
| 11 | med | Update RotatingFileHandler docs from "10MB" to "~9.8MB" | docs (app-factory.md) |
| 12 | med | Document `RATE_LIMIT_STORAGE_URI` production default | docs (configuration.md) |
| 13 | low | Add detailed model sections for Subscriber, Tag, PageView, ShareEvent | docs (models.md) |
| 14 | low | Add `SEARCH_PROVIDER` and `SEARCH_CONFIG` to `__all__` in config.py | source (app/config.py) |
| 15 | low | Review `SiteSettings.get_instance()` unconditional commit pattern | source (app/models.py) |
| 16 | low | Consider documenting connection pool settings for non-SQLite databases | docs (app-factory.md) |
| 17 | low | Document `SESSION_COOKIE_HTTPONLY` setting | docs (app-factory.md) |
| 18 | low | Document `login_manager.login_message` attribute | docs (app-factory.md) |
