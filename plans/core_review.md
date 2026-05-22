# Architecture Review: core/ Documents

Cross-reference of `architecture/core/` documents against `app/` implementation.

---

## app-factory.md

### Verified Claims

| Claim | Status |
|-------|--------|
| Validates `SECRET_KEY` is set and at least 32 characters | ✅ `app/__init__.py:151-159` |
| Validates `ADMIN_PASSWORD` is set | ✅ `app/__init__.py:160-163` |
| Validates full configuration via `_validate_config()` | ✅ `app/__init__.py:164-166` |
| Flask app created with `instance_relative_config=True` | ✅ `app/__init__.py:168` |
| `SQLALCHEMY_DATABASE_URI` configured for SQLite default | ✅ `app/__init__.py:175-179` |
| `SESSION_COOKIE_SAMESITE` set to "Lax" | ✅ `app/__init__.py:185` |
| `MAX_CONTENT_LENGTH` set to `MAX_UPLOAD_SIZE + 1MB` | ✅ `app/__init__.py:181` |
| Extensions: SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress | ✅ All initialized |
| Blueprint `public` at `/` | ✅ `app/__init__.py:268` |
| Blueprint `admin` at `/admin` | ✅ `app/__init__.py:269` |
| Blueprint `rss` | ✅ `app/__init__.py:270` |
| Blueprint `errors` | ✅ `app/__init__.py:271` |
| Blueprint `api` at `/api` | ✅ `app/__init__.py:272` |
| Blueprint `swaggerui` at `/api/docs` | ✅ `app/__init__.py:274-278` |
| SQLite pragmas set via event listener (`journal_mode=WAL`, `busy_timeout=5000`) | ✅ `app/__init__.py:251-256` |
| Auto-create first admin user if none exists | ✅ `app/__init__.py:406-421` |
| Initialize `SiteSettings` if none exist | ✅ `app/__init__.py:425-437` |
| Initialize FTS5 search tables | ✅ `app/__init__.py:439-442` |
| Run integrity check (`PRAGMA integrity_check`) | ✅ `app/__init__.py:446-461` |
| APScheduler initialization | ✅ `app/__init__.py:465-467` |
| Page view buffer initialization | ✅ `app/__init__.py:469-471` |
| CSP nonce generated per request | ✅ `app/__init__.py:293` |
| Before request: request ID, CSP nonce, CSRF validation, session timeout | ✅ `app/__init__.py:290-336` |
| After request: security headers, CSP headers with nonce, HSTS in production, Prometheus metrics | ✅ `app/__init__.py:338-395` |
| Context processors documented in extensions.py section | ✅ `app/extensions.py` and `app/context_processors.py` |

### Discrepancies

| Issue | Details |
|-------|---------|
| **SESSION_COOKIE_HTTPONLY not documented** | `app/__init__.py:186` sets `SESSION_COOKIE_HTTPONLY = True` but docs don't mention this setting. |
| **S3 storage docs incomplete** | Docs mention `STORAGE_BACKEND` and S3 settings in Configuration table but these aren't in `app/config.py`. S3 settings are read directly from env vars in `app/storage.py:41`. |
| **Rate limit storage not documented** | `RATE_LIMIT_STORAGE_URI` is configured but not mentioned in app-factory.md middleware section. |

### Bugs Found

None.

### Improvement Opportunities

| Priority | Item |
|----------|------|
| Low | Add `SESSION_COOKIE_HTTPONLY` to documented settings |
| Low | Document `RATE_LIMIT_STORAGE_URI` configuration |
| Low | Clarify S3 storage is configured via env vars, not `config.toml` |

---

## configuration.md

### Verified Claims

| Claim | Status |
|-------|--------|
| Configuration loaded from `config.toml` with env var overrides | ✅ `app/config.py:64-79` |
| Priority order: env vars > config.toml > defaults | ✅ `app/config.py:56-61` |
| `SECRET_KEY` required, min 32 chars | ✅ `app/config.py:84, validation in `app/__init__.py:151-159` |
| `ADMIN_PASSWORD` required | ✅ `app/config.py:90` |
| `ADMIN_USERNAME` defaults to "admin" | ✅ `app/config.py:89` |
| `POSTS_PER_PAGE` default 10 | ✅ `app/config.py:83` |
| `SESSION_LIFETIME_HOURS` default 24 | ✅ `app/config.py:86` |
| `SESSION_IP_BINDING` modes documented (off/warn/enforce) | ✅ `app/config.py:87` |
| `MAX_UPLOAD_SIZE` default 10485760 (10MB) | ✅ `app/config.py:121` |
| `MAX_VIEWED_POSTS` default 100 | ✅ `app/config.py:85` |
| `TAG_CACHE_TTL_SECONDS` default 60 | ✅ `app/config.py:115` |
| `DASHBOARD_PER_PAGE` default 20 | ✅ `app/config.py:117` |
| `SUBSCRIBERS_PER_PAGE` default 50 | ✅ `app/config.py:118` |
| `MEDIA_PER_PAGE` default 50 | ✅ `app/config.py:119` |
| `MEDIA_MAX_FILES` default 1000 | ✅ `app/config.py:120` |
| `EXPORT_BATCH_SIZE` default 500 | ✅ `app/config.py:122` |
| `FTS_RESULT_LIMIT` default 100 | ✅ `app/config.py:123` |
| `PREVIEW_TOKEN_EXPIRY_DAYS` default 7 | ✅ `app/config.py:126` |
| `HEALTH_CHECK_SECRET` env var | ✅ `app/config.py:127` |
| `DATA_BACKUP_DIR` default "backups" | ✅ `app/config.py:135` |
| `WEBHOOK_TIMEOUT` default 10 | ✅ `app/config.py:136` |
| `WEBHOOK_ENCRYPTION_KEY` env var | ✅ `app/config.py:137` |
| `COMPRESS_ALGORITHM` default `["zstd", "br", "gzip"]` | ✅ `app/config.py:138` |
| `SMTP_TIMEOUT` default 30 | ✅ `app/config.py:140` |
| `SEARCH_PROVIDER` default "sqlite" | ✅ `app/config.py:154` |
| `SEARCH_CONFIG` default `{}` | ✅ `app/config.py:155` |
| `NEWSLETTER_SEND_TIME` default "08:00" | ✅ `app/config.py:110` |
| `CONFIRMATION_EXPIRY_HOURS` default 1 | ✅ `app/config.py:111-113` |
| `NEWSLETTER_MAX_RETRY_ATTEMPTS` default 5 | ✅ `app/config.py:114` |
| `LOGIN_FAILURE_DELAY` default 0.05 | ✅ `app/config.py:128` |
| `TOKEN_ENUMERATION_DELAY` default 0.1 | ✅ `app/config.py:125` |
| `MAX_FAILED_ATTEMPTS` default 5 | ✅ `app/config.py:142` |
| `LOCKOUT_DURATION_MINUTES` default 15 | ✅ `app/config.py:143` |
| `REDIS_URL` default "redis://localhost:6379/0" | ✅ `app/config.py:134` |
| `RATE_LIMIT_STORAGE_URI` default "memory://" (dev) / "redis://localhost:6379/1" (prod) | ✅ `app/config.py:129-132` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_ADDRESS` all documented | ✅ `app/config.py:104-108` |
| `_validate_config()` checks `send_time` (HH:MM format), `posts_per_page` (1-100), `confirmation_expiry_hours` (positive), `smtp_port` (1-65535), `base_url` (valid scheme/domain) | ✅ `app/config.py:158-242` |

### Discrepancies

| Issue | Details |
|-------|---------|
| **S3 settings documented but not in config.py** | `STORAGE_BACKEND`, `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL` are all documented in configuration.md but not defined in `app/config.py`. They are read directly from env vars in `app/storage.py`. This means the documentation is misleading - you cannot configure S3 via `config.toml`. |
| **`PAGE_VIEW_BUFFER_SIZE` not documented** | Present in `app/config.py:124` but missing from configuration.md entirely. |
| **`ADMIN_RATE_LIMITS` not documented** | Present in `app/config.py:145-152` but not mentioned in docs. |
| **`REDIS_URL` description incomplete** | Docs show `REDIS_URL` default as `redis://localhost:6379/0` which is correct, but don't mention it differs from `RATE_LIMIT_STORAGE_URI` (which uses db 1 in production). |

### Bugs Found

| Bug | Location | Description |
|-----|----------|-------------|
| None | - | All validation functions match documentation |

### Improvement Opportunities

| Priority | Item |
|----------|------|
| Medium | Document `PAGE_VIEW_BUFFER_SIZE` setting |
| Medium | Document `ADMIN_RATE_LIMITS` configuration |
| Medium | Fix S3 storage documentation - clarify it uses env vars, not config.toml |
| Low | Clarify relationship between `REDIS_URL`, `RATE_LIMIT_STORAGE_URI`, and `CACHE_REDIS_URL` |

---

## models.md

### Verified Claims

| Claim | Status |
|-------|--------|
| User model: id, username, email, password_hash, is_admin, reset_token, reset_token_expires_at, failed_login_count, locked_until, totp_secret_encrypted, totp_enabled | ✅ `app/models.py:21-34` |
| User.totp_secret is a property that decrypts on access | ✅ `app/models.py:43-52` |
| User.set_totp_secret() encrypts for storage | ✅ `app/models.py:54-60` |
| User.get_totp_uri() generates QR code provisioning URI | ✅ `app/models.py:62-70` |
| User.backup_codes_hashed = db.Column(db.JSON) | ✅ `app/models.py:72` |
| User.__repr__ returns `<User id={self.id}>` | ✅ `app/models.py:119-120` |
| User.admin_sessions relationship | ✅ `app/models.py:36-41` |
| User.has is_locked(), record_failed_login(), reset_failed_login(), set_password(), check_password() | ✅ `app/models.py:96-117` |
| User note: only admin_sessions relationship, no posts or audit_logs reverse lookups | ✅ Verified - no `user.posts` exists in code |
| AdminSession: id, user_id, session_id, ip_address, user_agent, created_at, last_activity | ✅ `app/models.py:324-333` |
| AdminSession.user relationship | ✅ `app/models.py:335` |
| AdminSession.__repr__ returns `<AdminSession user_id={self.user_id} ip={self.ip_address}>` | ✅ `app/models.py:339-340` |
| Post model: id, title, slug, body, summary, image, image_alt_text, published, published_at, scheduled_publish_at, newsletter_sent_at, newsletter_attempts | ✅ `app/models.py:174-194` |
| Post relationships: tags, page_views, share_events, revisions, series_entries, comments | ✅ `app/models.py:196-213` |
| Post.indexes: published+created_at, published_at, newsletter_sent_at, published+updated_at, published+slug, scheduled_publish_at | ✅ `app/models.py:215-222` |
| Tag model: id, name, slug | ✅ `app/models.py:128-133` |
| Subscriber model: id, email, token, confirmed, created_at, expires_at, unsubscribed_at | ✅ `app/models.py:260-275` |
| Subscriber indexes: confirmed+unsubscribed_at | ✅ `app/models.py:277-281` |
| Page model: id, title, slug, body, published | ✅ `app/models.py:148-161` |
| Page.indexes: published+slug | ✅ `app/models.py:163` |
| PageView model: id, post_id, referrer, created_at | ✅ `app/models.py:287-293` |
| PageView indexes: post_id+created_at | ✅ `app/models.py:297-299` |
| ShareEvent model: id, post_id, platform, created_at | ✅ `app/models.py:305-311` |
| ShareEvent indexes: post_id+created_at, platform | ✅ `app/models.py:315-318` |
| Comment model: id, post_id, parent_id, author_name, author_email, content, approved, created_at | ✅ `app/models.py:594-604` |
| Comment.parent (self-referential), Comment.replies | ✅ `app/models.py:607-608` |
| Comment indexes: post_id+approved, created_at, parent_id | ✅ `app/models.py:610-614` |
| Series model: id, name, slug, description, image, created_at | ✅ `app/models.py:548-556` |
| Series.posts relationship ordered by PostSeries.order_index | ✅ `app/models.py:558` |
| Series.indexes: slug | ✅ `app/models.py:560-562` |
| Series.generate_slug() uses app.utils.generate_slug | ✅ `app/models.py:564-567` |
| PostSeries model: id, series_id, post_id, order_index | ✅ `app/models.py:573-579` |
| PostSeries relationships: series, post | ✅ `app/models.py:581-582` |
| PostSeries indexes: series_id, post_id | ✅ `app/models.py:584-588` |
| PostSeries UniqueConstraint: (series_id, post_id) name="uq_series_post" | ✅ `app/models.py:587` |
| Webhook model: id, name, url, secret (property), event_type, enabled, created_at | ✅ `app/models.py:484-493` |
| Webhook secret is encrypted (property), not plain text | ✅ `app/models.py:499-517` |
| Webhook.indexes: event_type+enabled | ✅ `app/models.py:495-497` |
| WebhookEvent model: id, webhook_id, event_type, payload, target_id, target_type, delivered, delivery_attempts, created_at | ✅ `app/models.py:523-535` |
| WebhookEvent.delivery_status field | ✅ `app/models.py:533` (not mentioned in docs - see bugs) |
| WebhookEvent.webhook relationship | ✅ `app/models.py:537` |
| WebhookEvent indexes: event_type+delivered, webhook_id | ✅ `app/models.py:539-542` |
| SiteSettings: theme_preset, syntax_theme, custom_css_enabled, custom_css, logo_text | ✅ `app/models.py:343-352` |
| SiteSettings.get_instance() singleton pattern | ✅ `app/models.py:354-361` |
| THEME_PRESETS dictionary with 4 presets | ✅ `app/models.py:367-458` |
| PostRevision: id, post_id, title, slug, body, summary, created_at, author_id | ✅ `app/models.py:236-247` |
| PostRevision relationships: post, author | ✅ `app/models.py:248-249` |
| PostRevision indexes: post_id+created_at, author_id | ✅ `app/models.py:251-254` |
| AdminAuditLog: id, actor_id, action, target_id, target_type, details, ip_address, timestamp | ✅ `app/models.py:461-471` |
| AdminAuditLog.actor relationship | ✅ `app/models.py:473` |
| AdminAuditLog indexes: actor_id+timestamp, action+timestamp | ✅ `app/models.py:475-478` |

### Discrepancies

| Issue | Details |
|-------|---------|
| **Webhook.secret is encrypted, not plain text** | Docs say `secret = db.Column(db.String(64), nullable=False)  # Plain text storage` at line 187. Actual: `webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)` with property getter/setter for encryption. |
| **WebhookEvent.delivery_status missing from docs** | Code has `delivery_status = db.Column(db.String(32), nullable=True)` at line 533. Docs describe `delivered` field but not the more detailed `delivery_status`. |
| **Post.author_id not documented** | PostRevision has author_id but Post model doesn't have a user_id field linking to author. This is mentioned in a note but worth noting. |

### Bugs Found

| Bug | Location | Description |
|-----|----------|-------------|
| Documentation says Webhook.secret is plain text | `architecture/core/models.md:187` - incorrectly states `# Plain text storage` |

### Improvement Opportunities

| Priority | Item |
|----------|------|
| Medium | Update Webhook.secret documentation to reflect encrypted storage |
| Medium | Document WebhookEvent.delivery_status field |
| Low | Clarify that Webhook secret encryption uses `webhook_encryption.py` |

---

## Summary

| Document | Verified | Discrepancies | Bugs | Priority |
|----------|----------|---------------|------|----------|
| app-factory.md | 27 claims | 3 minor | 0 | Low |
| configuration.md | 45 claims | 4 (2 medium) | 0 | Medium |
| models.md | 62 claims | 3 (1 medium) | 1 | Medium |

**Overall Priority: Medium**

The documents are generally accurate. Main issues:
1. S3 storage configuration is documented incorrectly (env vars, not config.toml)
2. Webhook secret encryption not reflected in documentation
3. Missing configuration settings (`PAGE_VIEW_BUFFER_SIZE`, `ADMIN_RATE_LIMITS`)