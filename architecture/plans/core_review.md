# Core Module Architecture Review

**Review Date:** 2026-05-09
**Reviewer:** core_reviewer
**Files Reviewed:**
- `/Users/davidbowman/projects/blog/architecture/core/app-factory.md`
- `/Users/davidbowman/projects/blog/architecture/core/configuration.md`
- `/Users/davidbowman/projects/blog/architecture/core/models.md`

**Source Code Cross-Referenced:**
- `app/__init__.py` (Flask app factory)
- `app/config.py` (configuration)
- `app/models.py` (models)
- `app/extensions.py` (extensions)
- `app/filters.py` (filters)
- `app/context_processors.py` (context processors)

---

## 1. Verified Accurate Claims

### App Factory (`app/__init__.py`)

| Claim | Status |
|-------|--------|
| Configuration validation (SECRET_KEY >= 32 chars, ADMIN_PASSWORD required) | VERIFIED |
| Flask app setup with `instance_relative_config=True` | VERIFIED |
| SQLite default with WAL mode | VERIFIED |
| Extensions: SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress | VERIFIED |
| Blueprints: public, admin, rss, errors, api, swaggerui | VERIFIED |
| Before request hooks: request_id, csp_nonce, CSRF validation, session timeout with sliding expiration | VERIFIED |
| After request: security headers, CSP with nonce, HSTS in production, Prometheus metrics | VERIFIED |
| Database initialization: first admin user, SiteSettings, FTS5, integrity check | VERIFIED |
| Background services: APScheduler, page view buffer | VERIFIED |

### Configuration (`app/config.py`)

| Claim | Status |
|-------|--------|
| Priority: Environment variables > config.toml > defaults | VERIFIED |
| Newsletter retry count default is 5 | VERIFIED |
| SMTP port validation (1-65535) | VERIFIED |
| base_url validation | VERIFIED |
| posts_per_page validation (1-100) | VERIFIED |
| Security settings: MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES, LOGIN_FAILURE_DELAY | VERIFIED |

### Models (`app/models.py`)

| Claim | Status |
|-------|--------|
| User.__repr__ returns `<User id={self.id}>` (PII/security) | VERIFIED (line 119-120) |
| Comment model self-referential parent/replies relationships | VERIFIED (lines 586-587) |
| Post model relationships: tags, page_views, share_events, revisions, series_entries, comments | VERIFIED |
| Indexes: ix_posts_published_created, ix_posts_published_at, ix_posts_published_updated, ix_posts_published_slug, ix_posts_newsletter_sent_at, ix_posts_scheduled_publish_at | VERIFIED |
| Index: ix_post_tags_tag_id | VERIFIED |
| Indexes: ix_subscribers_confirmed_unsubscribed, ix_comments_post_approved, ix_comments_created_at, ix_comments_parent_id | VERIFIED |
| AdminAuditLog relationship to User via actor_id | VERIFIED |
| THEME_PRESETS dictionary with github-dark, github-light, solarized-dark, monokai | VERIFIED |
| Subscriber.expires_at field | VERIFIED (line 270) |

### Extensions (`app/extensions.py`)

| Claim | Status |
|-------|--------|
| SQLAlchemy, LoginManager, Migrate initialization | VERIFIED |
| login_view = "admin.login" | VERIFIED |
| session_protection = "strong" | VERIFIED |

### Context Processors (`app/context_processors.py`)

| Claim | Status |
|-------|--------|
| inject_csrf() - csrf_token, csp_nonce | VERIFIED |
| inject_config() - site config variables | VERIFIED |
| inject_theme() - theme settings | VERIFIED |
| inject_footer_data() - footer data | VERIFIED |
| inject_show_footer_posts() - boolean | VERIFIED |

### Template Filters (`app/filters.py`)

| Claim | Status |
|-------|--------|
| markdown_safe, reading_time, sanitize_css, post_image_url, post_image_srcset, post_image_avif_url | VERIFIED |

---

## 2. Inaccurate/Outdated Claims

### `app-factory.md` - SESSION_COOKIE_SECURE (Line 18)

**Issue:** Claims `SESSION_COOKIE_SECURE` is `True (in production)`.

**Actual Behavior:** The code at lines 182-184 shows:
```python
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE", "true"
).lower() in ("true", "1", "yes")
```
It defaults to `"true"` string, not `True` boolean, and is configurable via environment variable. It only raises an error if `False` in production mode (lines 197-201).

**Correction:** Update to reflect actual behavior: defaults to "true" string, configurable via `SESSION_COOKIE_SECURE` env var, raises error if explicitly set to False in production.

---

### `app-factory.md` - SQLite Pragmas Section (Lines 57-61)

**Issue:** Section shows static PRAGMA commands:
```python
PRAGMA journal_mode=WAL
PRAGMA busy_timeout=5000
```

**Actual Behavior:** These are set via SQLAlchemy event listener at lines 251-256, not as static commands:
```python
@event.listens_for(db.engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
```

**Correction:** Document that pragmas are set via SQLAlchemy connect event listener, not static PRAGMA statements.

---

### `models.md` - User Model totp_secret Field (Line 97)

**Issue:** Documentation shows:
```python
totp_secret = db.Column(db.String(32))  # 2FA secret
```

**Actual Behavior:** The model does not have a `totp_secret` column. The actual field is:
```python
totp_secret_encrypted = db.Column(db.String(256), nullable=True)  # line 33
totp_enabled = db.Column(db.Boolean, default=False, nullable=False)  # line 34
```

The `totp_secret` is a **property** (lines 43-52) that decrypts on access:
```python
@property
def totp_secret(self) -> Optional[str]:
    """Get decrypted TOTP secret."""
    if not self.totp_secret_encrypted:
        return None
    from app.services.encryption import decrypt
    try:
        return decrypt(self.totp_secret_encrypted)
    except Exception:
        return None
```

**Correction:** Document `totp_secret_encrypted` column and `totp_enabled` field. Clarify that `totp_secret` is a property that decrypts the encrypted value on access, and that TOTP secrets are encrypted at rest using AES-256-GCM.

---

### `models.md` - User Model Backup Codes (Missing Documentation)

**Issue:** The User model has backup codes functionality (lines 72-94) that is not documented:
- `backup_codes_hashed` - JSON column storing SHA-256 hashed codes
- `generate_backup_codes()` - generates 8 backup codes
- `verify_backup_code()` - verifies and consumes a code

**Correction:** Add documentation for backup codes feature.

---

### `configuration.md` - Missing Settings

**Issue:** Several configuration settings documented in `config.py` are missing from `configuration.md`:

| Missing Setting | Location in config.py | Default |
|----------------|----------------------|---------|
| `MAX_VIEWED_POSTS` | Line 85 | 100 |
| `TAG_CACHE_TTL_SECONDS` | Line 115 | 60 |
| `DASHBOARD_PER_PAGE` | Line 117 | 20 |
| `SUBSCRIBERS_PER_PAGE` | Line 118 | 50 |
| `MEDIA_PER_PAGE` | Line 119 | 50 |
| `MEDIA_MAX_FILES` | Line 120 | 1000 |
| `EXPORT_BATCH_SIZE` | Line 122 | 500 |
| `FTS_RESULT_LIMIT` | Line 123 | 100 |
| `PREVIEW_TOKEN_EXPIRY_DAYS` | Line 126 | 7 |
| `HEALTH_CHECK_SECRET` | Line 127 | "" |
| `DATA_BACKUP_DIR` | Line 135 | "backups" |
| `WEBHOOK_TIMEOUT` | Line 136 | 10 |
| `WEBHOOK_ENCRYPTION_KEY` | Line 137 | "" |
| `COMPRESS_ALGORITHM` | Line 138 | ["zstd", "br", "gzip"] |
| `SMTP_TIMEOUT` | Line 140 | 30 |
| `SEARCH_PROVIDER` | Line 154 | "sqlite" |
| `SEARCH_CONFIG` | Line 155 | {} |

**Correction:** Add sections for these settings.

---

### `configuration.md` - SESSION_IP_BINDING Values (Line 16)

**Issue:** Documents `session_ip_binding = "warn"` but doesn't explain behavior.

**Actual Behavior (from `app/routes/admin/__init__.py` lines 32-54):**
- `"warn"` (default): Logs warning on IP change but allows session
- `"enforce"`: Invalidates session and requires re-login

**Correction:** Document both modes with their actual behavior.

---

### `models.md` - Comment Model author_email (Line 147)

**Issue:** Documentation shows `author_email = db.Column(db.String(256))` without nullable status.

**Actual Behavior (line 580):** `author_email = db.Column(db.String(256), nullable=False)` - it is NOT nullable.

**Correction:** Mark author_email as required (nullable=False).

---

## 3. Missing Documentation

### Models

The following models/relationships are not documented in `models.md`:

1. **AdminSession Model** - Fully implemented but not documented:
   - `user_id`, `session_id`, `ip_address`, `user_agent`, `created_at`, `last_activity`
   - Used for session tracking and IP binding
   - See `models.py:324-341`

2. **Series Model** - Not documented:
   - `name`, `slug`, `description`, `image`, `created_at`
   - `posts` relationship via PostSeries
   - See `models.py:527-550`

3. **PostSeries Model** - Not documented:
   - Junction table linking Series and Post
   - `series_id`, `post_id`, `order_index`
   - Unique constraint on series_id + post_id
   - See `models.py:552-571`

4. **Webhook Model** - Not documented:
   - `name`, `url`, `secret`, `event_type`, `enabled`, `created_at`
   - See `models.py:484-501`

5. **WebhookEvent Model** - Not documented:
   - `webhook_id`, `event_type`, `payload`, `target_id`, `target_type`, `delivered`, `delivery_attempts`, `created_at`
   - See `models.py:503-525`

6. **PostRevision Model** - Partially documented, missing `author_id` field:
   - `post_id`, `title`, `slug`, `body`, `summary`, `created_at`, `author_id`
   - `author` relationship
   - See `models.py:236-258`

### Services

1. **Encryption Service** (`app/services/encryption.py`) - TOTP encryption using AES-256-GCM
2. **Backup Service** (`app/services/backup.py`) - Database backup with encryption/compression
3. **Slug Service** (`app/services/slug.py`) - Slug generation with collision handling
4. **Storage Service** (`app/storage.py`) - Local and S3 storage backends

### Security Features

1. **2FA Implementation** - TOTP setup/verify routes, backup codes
2. **Rate Limiting** - ADMIN_RATE_LIMITS configuration
3. **Account Lockout** - failed_login_count, locked_until

### Context Processors

1. **Cache Invalidation Functions**:
   - `invalidate_settings_cache()`
   - `invalidate_footer_cache()`

---

## 4. Potential Issues

### Security Issue: CSP nonce used in both regular and Report-Only headers

In `app/__init__.py` lines 356-378, the CSP header includes the nonce:
```python
response.headers["Content-Security-Policy"] = (
    f"default-src 'self'; "
    f"style-src 'self' 'nonce-{nonce}'; "
    ...
)
```

And in debug mode, a Report-Only header is also set with the same nonce. This is fine for testing but ensure Report-Only is not used in production inadvertently.

### Security Issue: LOGIN_FAILURE_DELAY only applied in auth.py

The `LOGIN_FAILURE_DELAY` (default 0.05s) is only applied in `auth.py` login handlers, not in other password-related operations. Verify this is intentional.

### Potential Bug: token_enumeration_delay documented but not validated for subscribe

The `TOKEN_ENUMERATION_DELAY` is used in `subscribe.py` but not validated in `_validate_config()` for the newsletter context. The validation only checks `token_enumeration_delay` in the app section (line 212-221).

### Issue: Page View Buffer Test Interference

As noted in `AGENTS.md`, the page view buffer (`app/page_view_buffer.py`) can cause test interference. This should be documented in the Core module documentation since it affects app factory behavior.

---

## 5. Recommended Improvements

### High Priority

1. **Fix User Model totp_secret documentation** - Document `totp_secret_encrypted` column and property, not a direct column
2. **Document AdminSession, Series, PostSeries, Webhook, WebhookEvent models** - These are implemented but missing from architecture docs
3. **Add missing configuration settings** - MAX_VIEWED_POSTS, DASHBOARD_PER_PAGE, MEDIA_* settings, SEARCH_*, WEBHOOK_*, etc.
4. **Document SESSION_IP_BINDING modes** - explain "warn" vs "enforce" behavior

### Medium Priority

5. **Document backup codes feature** in User model
6. **Document 2FA implementation** - routes, TOTP encryption, backup codes
7. **Document rate limiting ADMIN_RATE_LIMITS** configuration
8. **Document encryption service** for TOTP secrets
9. **Update SQLite PRAGMA documentation** - clarify they are set via SQLAlchemy event listener

### Low Priority

10. **Add health check endpoint documentation** if it exists
11. **Document page view buffer** initialization and test considerations
12. **Document COMPRESS_ALGORITHM** options
13. **Add storage backend documentation** - local vs S3

---

## Summary of Key Findings

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 25+ |
| Inaccurate/Outdated Claims | 6 |
| Missing Documentation | 15+ items |
| Potential Issues | 4 |

The core architecture documentation is largely accurate but has several areas requiring updates, particularly:

1. **Critical**: User model's `totp_secret` is documented as a column when it's actually an encrypted property
2. **High**: Several models (AdminSession, Series, PostSeries, Webhook, WebhookEvent) completely missing
3. **High**: ~17 configuration settings missing from documentation
4. **Medium**: SESSION_IP_BINDING behavior not fully documented
5. **Low**: Various security features and services not documented
