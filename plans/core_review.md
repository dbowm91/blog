# Core Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** app-factory.md, configuration.md, models.md
**Source Files:** app/__init__.py, app/config.py, app/models.py, app/extensions.py, app/filters.py, app/context_processors.py

## Findings

### Verified Claims (Correct)
- SECRET_KEY validation: set and at least 32 characters (config.py:91, __init__.py:151-158)
- ADMIN_PASSWORD required (config.py:97, __init__.py:160-163)
- Flask app created with `instance_relative_config=True` (__init__.py:168)
- Extensions: SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress — all 6 initialized in correct order (extensions.py + __init__.py:200-234)
- Blueprints: public (no prefix), admin (url_prefix="/admin"), rss (no prefix), errors, api (url_prefix="/api"), swaggerui (url_prefix="/api/docs") — all confirmed
- Before request: generates g.request_id, g.csp_nonce, CSRF validation for POST, session timeout check (__init__.py:289-331)
- After request: security headers, CSP with nonce, HSTS in production, Prometheus metrics (__init__.py:333-386)
- SQLite pragmas: journal_mode=WAL, busy_timeout=5000 via event listener (__init__.py:249-254)
- Database init: auto-create admin user, SiteSettings init, FTS5 init, integrity check (__init__.py:392-453)
- APScheduler + page view buffer initialization (__init__.py:455-462)
- All CLI commands listed in app-factory.md exist in app/cli.py (rebuild-search, cleanup-orphaned-images, create-admin, promote-admin, check-integrity, export-data, import-data, seed)
- Vite integration registers vite_asset() as Jinja2 global (__init__.py:468-470, vite.py:81-83)
- StructuredLogFormatter outputs JSON with timestamp, level, request_id, message (__init__.py:79-118)
- RotatingFileHandler: 10MB max, 10 backups, INFO level (__init__.py:138-146)
- ProxyFix: PROXY_COUNT env var, default 1 (__init__.py:185-186)
- Cache: RedisCache in production (prefix blog_, 300s TTL), SimpleCache in dev (__init__.py:221-233)
- CSP headers match doc exactly (__init__.py:347-357)
- Context processors provide csrf_token, csp_nonce, site_title, site_description, author_*, base_url, current_year, canonical_url, theme_*, recent_posts_*, footer_tags, show_footer_posts
- Extensions code block matches extensions.py exactly (extensions.py:1-10)
- All 17 model classes present in app/models.py
- User model fields, relationships, methods all match (models.py:21-126)
- AdminSession model fields, relationships, indexes match (models.py:323-339)
- Webhook model fields, property accessors match (models.py:483-519)
- Series model fields, relationships match (models.py:549-572)
- PostSeries model fields, relationships, UniqueConstraint match (models.py:575-593)
- PostRevision model fields, relationships match (models.py:241-262)
- Page model fields match (models.py:153-177)
- SiteSettings model fields, get_instance() classmethod match (models.py:342-363)
- ApiToken model fields, is_valid(), has_scope() match (models.py:625-657)
- Configuration priority (env > config.toml > defaults) confirmed in config.py
- Theme presets: github-dark, github-light, solarized-dark, monokai (models.py:366-457)
- All 30 indexes listed in models.md Key Indexes section are correct and match code

### Discrepancies (Doc vs Code)

- **app-factory.md:178 | extensions.py:8** — Code block omits `login_manager.login_message = "Please log in to access this page."` which exists in extensions.py line 8. The doc only shows `login_view` and `session_protection`.

- **app-factory.md:47-51 | __init__.py:294** — Before Request hooks section omits `g.request_start_time = time.perf_counter()` (line 294). This is used by the Prometheus metrics collection in `set_security_headers` (line 374-376). Doc should document this as it's part of the before-request pipeline.

- **app-factory.md:84-98 | cli.py:264-268** — Doc says `flask seed` has "options: `--posts`, `--subscribers`, `--published`". Actual CLI definition has `--posts`, `--subscribers`, and `--published/--draft` (a boolean flag pair, not a standalone option). The `--draft` variant is missing from documentation.

- **configuration.md:141 | config.py:145-148** — Doc claims `LOGIN_FAILURE_DELAY` default is `0.05` with "no minimum enforced". Code applies `max(LOGIN_FAILURE_DELAY, 0.1)` on line 148, enforcing a minimum of 0.1 seconds. The doc is factually incorrect about "no minimum enforced".

- **configuration.md:146 | config.py:165-172** — Doc references `app/config.py:164-171` for `ADMIN_RATE_LIMITS`. Actual code is at lines 165-172 (off by 1 line start, off by 1 line end).

- **configuration.md:115-125 | storage.py:53-60** — Storage Settings section (STORAGE_BACKEND, S3_BUCKET, S3_REGION, etc.) documents these as config variables in `app/config.py`, but they are NOT in `app/config.py` at all. They are defined as `os.environ.get()` calls in `app/storage.py` (lines 53-60). The configuration.md incorrectly attributes these to the config module.

- **models.md:299-302 | models.py:184-187** — Post model code block omits `nullable=False` on `title`, `slug`, `body`. Actual code has `nullable=False` on all three.

- **models.md:303-304 | models.py:188-189** — Post model code block omits `nullable=True` on `image` and `image_alt_text`. Actual code explicitly specifies `nullable=True`.

- **models.md:308-310 | models.py:197-199** — Post model code block omits `nullable=True` on `published_at`, `scheduled_publish_at`, `newsletter_sent_at`.

- **models.md:311 | models.py:200** — Post model `newsletter_attempts` shown without `nullable=False`. Code has `nullable=False`.

- **models.md:297-320 | models.py:219-226** — Post model code block entirely omits `__table_args__` with 6 indexes. This is significant for anyone implementing queries against the Post model.

- **models.md:314 | models.py:202** — Post model `tags` relationship shown as `db.relationship("Tag", secondary=post_tags)` but actual code includes `back_populates="posts"`.

- **models.md:327 | models.py:600** — Comment model `post_id` shown without `nullable=False`. Code has `nullable=False`.

- **models.md:328 | models.py:601** — Comment model `parent_id` shown without `nullable=True`. Code has `nullable=True`.

- **models.md:329 | models.py:602** — Comment model `author_name` shown without `nullable=False`. Code has `nullable=False`.

- **models.md:331 | models.py:604** — Comment model `content` shown without `nullable=False`. Code has `nullable=False`.

- **models.md:332 | models.py:605** — Comment model `approved` shown without `nullable=False`. Code has `nullable=False`.

- **models.md:322-340** — Comment model code block entirely omits `__table_args__` with 4 indexes (ix_comments_post_approved, ix_comments_created_at, ix_comments_parent_id, ix_comments_is_spam).

- **models.md:347-349 | models.py:157-159** — Page model `title`, `slug`, `body` shown without `nullable=False`. Code has `nullable=False` on all three.

- **models.md:342-355** — Page model code block entirely omits `__table_args__` with index (ix_pages_published_slug).

- **models.md:368-373 | models.py:346-351** — SiteSettings model fields shown without `nullable=False`. Code has `nullable=False` on theme_preset, syntax_theme, custom_css_enabled, custom_css, logo_text.

- **models.md:268 | models.py:593** — PostSeries `__repr__` documented as `<PostSeries series={series_id} post={post_id}>` but actual code returns `<PostSeries series_id={self.series_id} post_id={self.post_id} order={self.order_index}>` (includes order_index, different field names).

- **models.md:208-227 | models.py:534-535** — WebhookEvent model code block omits two fields that exist in code: `successful_deliveries = db.Column(db.Integer, default=0, nullable=False)` and `failed_deliveries = db.Column(db.Integer, default=0, nullable=False)`.

- **models.md Key Indexes section** — Missing indexes for 5 models:
  - AdminSession: `ix_admin_sessions_user_id` (user_id)
  - Webhooks: `ix_webhooks_event_type_enabled` (event_type, enabled)
  - WebhookEvent: `ix_webhook_events_event_type_delivered` (event_type, delivered), `ix_webhook_events_webhook_id` (webhook_id)
  - Series: `ix_series_slug` (slug)
  - ApiToken: `ix_api_tokens_token_hash` (token_hash), `ix_api_tokens_revoked_at` (revoked_at)

- **configuration.md:176-183 | config.py:214-250** — Validation section documents only 5 validations (send_time, posts_per_page, confirmation_expiry_hours, smtp_port, base_url). Code also validates: dashboard_per_page, subscribers_per_page, media_per_page, media_max_files, max_upload_size, export_batch_size, fts_result_limit (config.py:214-230), token_enumeration_delay (config.py:232-241), and smtp_timeout (config.py:243-250). 8 additional validations are undocumented.

### Missing Documentation

- **CSRF Sliding Window** — `app/csrf.py` implements a sliding window of 5 valid tokens per session with rotation. This mechanism (window size, rotation behavior, X-CSRF-Token header support) is not documented in any architecture doc.

- **Page View Buffer** — `app/page_view_buffer.py` implements buffered page view writes with configurable flush size and interval. The flush interval (`PAGE_VIEW_FLUSH_INTERVAL` env var, default 5s) and shutdown handling are not documented.

- **Search Fallback** — `app/search.py` implements LIKE fallback when FTS5 is unavailable, "Did you mean?" suggestions, search snippet generation, and query term highlighting. None of this is documented.

- **Tag Cache** — `app/tag_cache.py` implements cached tag counts with configurable TTL. Not documented.

- **CSS Sanitization** — `app/utils.py` `sanitize_css()` uses tinycss2 with property allowlist. Not documented.

- **Storage Backend Details** — `app/storage.py` implements LocalStorageBackend and S3StorageBackend with thread-safe singleton pattern, variant deletion, and upload processing. Architecture docs only reference env vars.

- **Request Start Time** — The before-request handler stores `g.request_start_time` for Prometheus latency measurement. Not documented.

- **`inject_show_footer_posts` path logic** — Context processor returns `show_footer_posts=False` for `/search` and `/tag/` paths. This filtering logic is not documented.

- **`inject_footer_data` path exclusion** — Footer data is empty for `/admin`, `/api`, `/rss` paths. Not documented.

### Potential Bugs / Concerns

- **X-Forwarded-For Spoofing** (`__init__.py:45-49`) — `get_client_ip()` trusts the raw `X-Forwarded-For` header. The `admin_required` decorator uses `request.remote_addr` (set by ProxyFix), but rate limiting via `get_client_ip()` can be bypassed by spoofing the header when not behind a trusted proxy. This inconsistency between IP sources for security decisions should be documented or addressed.

- **Backup Codes Unsalted SHA-256** (`models.py:77-100`) — `generate_backup_codes()` and `verify_backup_code()` use plain SHA-256 without salt. While the codes are high-entropy (32 hex chars), using proper password hashing (bcrypt/argon2) would provide defense-in-depth. The lack of salt means identical codes across users produce identical hashes.

- **`_get_footer_data` Redundant Query** (`context_processors.py:97-103`) — Two separate queries fetch `recent_posts_footer` (limit 3) and `recent_posts_sidebar` (limit 5). The sidebar query is a superset. Could be optimized to one query with limit 5 and slicing.

- **`StructuredLogFormatter` Info Leak Risk** (`__init__.py:91-117`) — The formatter adds all non-excluded `record.__dict__` keys to JSON output. Any extra attributes attached to log records (e.g., via third-party libraries) could be inadvertently logged.

- **`post_image_srcset_filter` Hardcoded Path** (`filters.py:72`) — URL construction hardcodes `/static/uploads/`. If the upload directory path changes, all srcset URLs break silently.

- **`SiteSettings.get_instance()` Race Condition** (`models.py:353-360`) — `get_instance()` reads then creates without row-level locking. Under concurrent requests, two processes could both see `None` and create duplicate instances. Should use `INSERT OR IGNORE` or `db.session.merge()`.

- **Admin Session Cleanup in Before-Request** (`__init__.py:314-326`) — Deleting `AdminSession` inside `before_request_handler` could fail if the session was already deleted by another process. The error handling catches this but it's a silent failure that could leave stale sessions.

- **Config Module Import-Time Failure** (`config.py:86`) — `_config = load_config()` runs at import time. If `config.toml` is missing, the import itself raises `RuntimeError` before any Flask error handling. This is intentional but could confuse developers expecting a more graceful error.

- **`inject_config` Timezone Assumption** (`context_processors.py:150`) — `datetime.now().year` uses system local time. At year boundaries, this could produce the wrong year if the server timezone differs from expected.

### Improvement Suggestions

1. **Add nullable constraints to model code blocks** — All model representations in models.md should include `nullable=` constraints as they exist in code. This prevents schema confusion during development.

2. **Add missing indexes to Key Indexes section** — The section currently covers 11 of 16 indexable models. Add indexes for AdminSession, Webhook, WebhookEvent, Series, and ApiToken.

3. **Fix LOGIN_FAILURE_DELAY documentation** — Update configuration.md to state minimum is 0.1 seconds, not "no minimum enforced."

4. **Move Storage Settings attribution** — Configuration.md Storage Settings section should reference `app/storage.py` as the source, not imply they are in `app/config.py`.

5. **Document CSRF mechanism** — Add a section covering the sliding window token rotation, X-CSRF-Token header support, and window size of 5.

6. **Document search fallback behavior** — Architecture docs should cover the LIKE fallback, "Did you mean?" suggestions, and snippet generation in search.py.

7. **Add g.request_start_time to before-request docs** — Include the Prometheus metrics start time tracking in the Before Request section.

8. **Document Page View Buffer** — Add architecture docs covering flush size, flush interval, and shutdown behavior.

9. **Fix PostSeries __repr__ in models.md** — Update the documented repr to match actual code output.

10. **Add WebhookEvent missing fields** — Add `successful_deliveries` and `failed_deliveries` to the WebhookEvent model documentation.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix `LOGIN_FAILURE_DELAY` doc: minimum is 0.1, not "no minimum enforced" | docs |
| 2 | high | Fix Storage Settings attribution: env vars are in `app/storage.py`, not `app/config.py` | docs |
| 3 | high | Add nullable constraints to all model code blocks in models.md | docs |
| 4 | high | Add 11 missing indexes to models.md Key Indexes section (AdminSession, Webhook, WebhookEvent, Series, ApiToken) | docs |
| 5 | high | Add `successful_deliveries` and `failed_deliveries` fields to WebhookEvent model doc | docs |
| 6 | medium | Fix PostSeries __repr__ to match actual code output | docs |
| 7 | medium | Add `login_manager.login_message` to extensions code block in app-factory.md | docs |
| 8 | medium | Add `g.request_start_time` to Before Request hooks documentation | docs |
| 9 | medium | Document CSRF sliding window mechanism (window size 5, token rotation) | docs |
| 10 | medium | Document search fallback, "Did you mean?", and snippet generation | docs |
| 11 | medium | Fix `flask seed` CLI doc: option is `--published/--draft`, not just `--published` | docs |
| 12 | medium | Add 8 missing validations to configuration.md Validation section | docs |
| 13 | medium | Fix ADMIN_RATE_LIMITS line reference: 165-172, not 164-171 | docs |
| 14 | low | Document Page View Buffer architecture (flush size, interval, shutdown) | docs |
| 15 | low | Document tag cache mechanism and TTL | docs |
| 16 | low | Document path-based footer exclusion logic (/admin, /api, /rss) | docs |
| 17 | low | Investigate X-Forwarded-For spoofing risk in get_client_ip() | source |
| 18 | low | Investigate SiteSettings.get_instance() race condition under concurrency | source |
| 19 | low | Consider optimizing _get_footer_data dual query to single query | source |
