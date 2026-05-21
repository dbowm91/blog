# Core Review: Architecture Documents vs Implementation

## Summary

Reviewed three architecture documents (`app-factory.md`, `configuration.md`, `models.md`) against actual code in `app/__init__.py`, `app/config.py`, `app/models.py`, `app/extensions.py`, and `app/context_processors.py`.

**Overall accuracy: High** - Most claims verified, but several discrepancies and one critical bug identified.

---

## Verified Claims

### App Factory (`app/__init__.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| Configuration validation (SECRET_KEY >= 32 chars, ADMIN_PASSWORD required) | ✅ Verified | `app/__init__.py:150-163` |
| Flask app setup with instance_relative_config=True | ✅ Verified | `app/__init__.py:168` |
| SESSION_COOKIE_SECURE defaults to True | ✅ Verified | `app/__init__.py:182-184` |
| SESSION_COOKIE_SAMESITE = "Lax" | ✅ Verified | `app/__init__.py:185` |
| MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE + 1MB | ✅ Verified | `app/__init__.py:181` |
| SQLite PRAGMA via event listener (WAL, busy_timeout) | ✅ Verified | `app/__init__.py:251-256` |
| Auto-create first admin user | ✅ Verified | `app/__init__.py:406-421` |
| Initialize SiteSettings if none exist | ✅ Verified | `app/__init__.py:425-437` |
| FTS5 search initialization | ✅ Verified | `app/__init__.py:439-442` |
| PRAGMA integrity_check | ✅ Verified | `app/__init__.py:446-461` |
| APScheduler initialization | ✅ Verified | `app/__init__.py:465-467` |
| Page view buffer initialization | ✅ Verified | `app/__init__.py:469-471` |
| Before request: request ID, CSP nonce | ✅ Verified | `app/__init__.py:292-295` |
| Before request: CSRF validation | ✅ Verified | `app/__init__.py:297-299` |
| Before request: session timeout check | ✅ Verified | `app/__init__.py:301-336` |
| After request: security headers | ✅ Verified | `app/__init__.py:339-395` |
| CSP header with nonce | ✅ Verified | `app/__init__.py:356-366` |
| HSTS in production | ✅ Verified | `app/__init__.py:352-355` |

### Extensions (`app/extensions.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| SQLAlchemy, LoginManager, Migrate initialized | ✅ Verified | `app/extensions.py:5-10` |
| login_view = "admin.login" | ✅ Verified | `app/extensions.py:7` |
| session_protection = "strong" | ✅ Verified | `app/extensions.py:9` |

### Context Processors (`app/context_processors.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| inject_csrf provides csrf_token, csp_nonce | ✅ Verified | `app/context_processors.py:138-148` |
| inject_config provides site config vars | ✅ Verified | `app/context_processors.py:150-161` |
| inject_theme provides theme settings | ✅ Verified | `app/context_processors.py:163-165` |
| inject_footer_data provides footer data | ✅ Verified | `app/context_processors.py:167-191` |
| inject_show_footer_posts provides boolean | ✅ Verified | `app/context_processors.py:193-200` |

### Configuration (`app/config.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| Loads from config.toml | ✅ Verified | `app/config.py:64-76` |
| Environment variable overrides | ✅ Verified | `_env()` function at `app/config.py:56-61` |
| _validate_config validates send_time, posts_per_page, etc. | ✅ Verified | `app/config.py:158-242` |
| SEARCH_PROVIDER, SEARCH_CONFIG | ✅ Verified | `app/config.py:154-155` |
| COMPRESS_ALGORITHM = ["zstd", "br", "gzip"] | ✅ Verified | `app/config.py:138` |

### Models (`app/models.py`)

| Model/Field | Status | Evidence |
|------------|--------|----------|
| User.admin_sessions relationship | ✅ Verified | `app/models.py:36-41` |
| User.totp_secret_encrypted property | ✅ Verified | `app/models.py:33, 43-52` |
| User.backup_codes_hashed (JSON) | ✅ Verified | `app/models.py:72` |
| User.__repr__ returns <User id={self.id}> | ✅ Verified | `app/models.py:119-120` |
| Post.tags (N:N via post_tags) | ✅ Verified | `app/models.py:13-18, 196-198` |
| Post.page_views, share_events, revisions, series_entries, comments | ✅ Verified | `app/models.py:199-213` |
| Post indexes (published, created_at), (published_at), etc. | ✅ Verified | `app/models.py:215-222` |
| PostRevision.post and PostRevision.author | ✅ Verified | `app/models.py:248-249` |
| Subscriber token, confirmed, unsubscribed_at | ✅ Verified | `app/models.py:260-285` |
| Comment self-referential parent/replies | ✅ Verified | `app/models.py:585-587` |
| Comment indexes (post_id, approved), (created_at), (parent_id) | ✅ Verified | `app/models.py:589-593` |
| AdminSession.user relationship | ✅ Verified | `app/models.py:335` |
| AdminSession user_id foreign key | ✅ Verified | `app/models.py:328` |
| SiteSettings.get_instance() singleton pattern | ✅ Verified | `app/models.py:354-361` |
| THEME_PRESETS dict | ✅ Verified | `app/models.py:367-458` |
| AdminAuditLog.actor relationship | ✅ Verified | `app/models.py:473` |
| Webhook.secret (not encrypted - plain storage) | ✅ Verified | `app/models.py:490` |
| WebhookEvent.webhook lazy="select" | ✅ Verified | `app/models.py:516` |
| PostSeries unique constraint (series_id, post_id) | ✅ Verified | `app/models.py:566` |
| Series.posts ordered by order_index | ✅ Verified | `app/models.py:537` |

---

## Discrepancies

### 1. Post Model Missing `user_id` Field

**Documentation:** `models.md:39` claims `user (reverse lookup: Post.user_id -> User.id)` relationship exists.

**Code:** `Post` model at `app/models.py:174-233` does **NOT** have a `user_id` column or any relationship to `User`.

**Impact:** Medium - This is a documentation error. The Post model does not track its author.

### 2. Post Model Missing `image` Documentation

**Documentation:** `models.md:256` mentions `image` as "Featured image" but `models.md:247-271` (Post Model Details) does not list the `image` field.

**Code:** `Post` model at `app/models.py:182-183` has `image` and `image_alt_text` fields.

**Impact:** Low - Missing documentation entry, not a contradiction.

### 3. Comment.author_email Not Marked as Required in Docs

**Documentation:** `models.md:281` shows `author_email = db.Column(db.String(256), nullable=False)` but this is in the Comment model code block. The relationship diagram at line 24 shows Comment without field details.

**Code:** Verified correct at `app/models.py:580`.

**Impact:** None - documentation is technically correct.

---

## Bugs Identified

### CRITICAL: Webhook.secret Stored in Plain Text

**Location:** `app/models.py:490`

**Issue:** The `Webhook.secret` field stores webhook secrets in plain text:
```python
secret = db.Column(db.String(64), nullable=False)
```

**Recommendation:** The `Webhook.secret` should be encrypted at rest like `User.totp_secret` using the `WEBHOOK_ENCRYPTION_KEY` config. The documentation at `models.md:172` says "Encrypted storage" which is incorrect.

**Severity:** High - Webhook secrets could be exposed if database is compromised.

**Recommended Fix:**
1. Add `webhook_secret_encrypted` column to Webhook model (like User model)
2. Add property getter/setter that encrypt/decrypt using `app.services.encryption`
3. Update all code that accesses `webhook.secret` to use the property

---

## Improvement Recommendations

### 1. Document Missing `user_id` on Post

**File:** `architecture/core/models.md`

**Change:** Remove the incorrect claim at line 39 about `user (reverse lookup: Post.user_id -> User.id)`. The Post model does not have a user_id field.

### 2. Add `image` and `image_alt_text` to Post Documentation

**File:** `architecture/core/models.md`

**Change:** Add `image` and `image_alt_text` fields to the Post model documentation around line 256-257.

### 3. Correct Webhook.secret Documentation

**File:** `architecture/core/models.md`

**Change:** Line 172 currently says `secret = db.Column(db.String(64), nullable=False)  # Encrypted storage`. Change to `# Plain text storage - consider encrypting for production`.

### 4. Add Missing Index: `ix_post_tags_tag_id`

**File:** `architecture/core/models.md`

**Change:** The documentation at line 72-73 shows `ix_post_tags_tag_id` under Tags section, but this index is actually on the `post_tags` junction table (line 17 in models.py: `db.Index("ix_post_tags_tag_id", "tag_id")`). Move this to a separate "Junction Tables" section or clarify it's on post_tags, not tags.

### 5. Add Index: `ix_page_views_post_created`

**File:** `architecture/core/models.md`

**Change:** Add missing index documented at `app/models.py:297-299`:
```
| Name | Columns |
|------|---------|
| `ix_page_views_post_created` | (post_id, created_at) |
```

### 6. Add Index: `ix_share_events_post_created` and `ix_share_events_platform`

**File:** `architecture/core/models.md`

**Change:** Add missing indexes documented at `app/models.py:315-318`:
```
| Name | Columns |
|------|---------|
| `ix_share_events_post_created` | (post_id, created_at) |
| `ix_share_events_platform` | (platform) |
```

### 7. Add Index: `ix_pages_published_slug`

**File:** `architecture/core/models.md`

**Change:** Add missing index documented at `app/models.py:163`:
```
| Name | Columns |
|------|---------|
| `ix_pages_published_slug` | (published, slug) |
```

### 8. Verify COMPRESS_ALGORITHM Default

**Documentation:** `configuration.md:80` says `COMPRESS_ALGORITHM` defaults to `["zstd", "br", "gzip"]`.

**Code:** Verified at `app/config.py:138`.

**Status:** ✅ Verified correct.

### 9. Missing `search` Configuration in config.toml Example

**Documentation:** `configuration.md` mentions `search.provider` and `search.config` for SEARCH_PROVIDER but the example TOML at lines 9-44 doesn't show a `[search]` section.

**Recommendation:** Add `[search]` section to the example config structure.

---

## Summary of Required Changes

| Priority | File | Change |
|----------|------|--------|
| High | `app/models.py` | Encrypt Webhook.secret at rest |
| High | `architecture/core/models.md` | Remove false claim about Post.user_id |
| Medium | `architecture/core/models.md` | Add missing Post fields (image, image_alt_text) |
| Medium | `architecture/core/models.md` | Correct Webhook.secret documentation |
| Medium | `architecture/core/models.md` | Add missing indexes (page_views, share_events, pages) |
| Low | `architecture/core/configuration.md` | Add [search] section to example config |
| Low | `architecture/core/models.md` | Clarify ix_post_tags_tag_id location |