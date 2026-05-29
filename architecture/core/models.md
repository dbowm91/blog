# Database Models (`app/models.py`)

The blog uses SQLAlchemy ORM with the following models:

## Model Overview

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | Admin users | username, password_hash, totp_secret_encrypted |
| `Post` | Blog posts | title, slug, body, published, published_at |
| `PostRevision` | Post edit history | title, slug, body, summary |
| `Tag` | Blog tags | name, slug |
| `Subscriber` | Newsletter subscribers | email, token, confirmed |
| `Page` | Static pages | title, slug, body, published |
| `PageView` | Analytics | post_id, referrer, created_at |
| `ShareEvent` | Social sharing | post_id, platform |
| `AdminSession` | Session tracking | user_id, session_id, ip_address |
| `SiteSettings` | Theme/settings | theme_preset, custom_css, logo_text |
| `AdminAuditLog` | Audit trail | actor_id, action, target_id |
| `Webhook` | Webhook endpoints | name, url, webhook_secret_encrypted, event_type |
| `WebhookEvent` | Webhook deliveries | event_type, payload, delivered, delivery_status |
| `Series` | Post series | name, slug, description |
| `PostSeries` | Series-post mapping | series_id, post_id, order_index |
| `Comment` | Post comments | post_id, parent_id, author_name, content |
| `ApiToken` | API authentication tokens | name, token_hash, scopes, expires_at, revoked_at |

## Relationships

```
User
└── admin_sessions (1:N, defined on User model)

Post
├── Tags (N:N via post_tags)
├── PostRevision (1:N)
├── PageView (1:N)
├── ShareEvent (1:N)
├── Comment (1:N)
├── PostSeries (1:N)

Subscriber
Tag
Page
Series
SiteSettings
Webhook
WebhookEvent

AdminAuditLog
└── actor (reverse lookup: AdminAuditLog.actor_id -> User.id)

Comment
├── parent (self-referential, 1:N for replies)
└── replies (back_populates)
```

## Key Indexes

### Posts
| Name | Columns |
|------|---------|
| `ix_posts_published_created` | (published, created_at) |
| `ix_posts_published_at` | (published_at) |
| `ix_posts_published_updated` | (published, updated_at) |
| `ix_posts_published_slug` | (published, slug) |
| `ix_posts_newsletter_sent_at` | (newsletter_sent_at) |
| `ix_posts_scheduled_publish_at` | (scheduled_publish_at) |

### Pages
| Name | Columns |
|------|---------|
| `ix_pages_published_slug` | (published, slug) |

### PageView
| Name | Columns |
|------|---------|
| `ix_page_views_post_created` | (post_id, created_at) |

### ShareEvent
| Name | Columns |
|------|---------|
| `ix_share_events_post_created` | (post_id, created_at) |
| `ix_share_events_platform` | (platform) |

### Tags
| Name | Columns |
|------|---------|
| `ix_post_tags_tag_id` | (tag_id) - Note: This index is on the `post_tags` junction table, not the `tags` table |

### Subscribers
| Name | Columns |
|------|---------|
| `ix_subscribers_confirmed_unsubscribed` | (confirmed, unsubscribed_at) |

### Comments
| Name | Columns |
|------|---------|
| `ix_comments_post_approved` | (post_id, approved) |
| `ix_comments_created_at` | (created_at) |
| `ix_comments_parent_id` | (parent_id) |
| `ix_comments_is_spam` | (is_spam) |

### PostSeries (Series-Post Mapping)
| Name | Columns |
|------|---------|
| `ix_post_series_series_id` | (series_id) |
| `ix_post_series_post_id` | (post_id) |

### PostRevision
| Name | Columns |
|------|---------|
| `ix_post_revisions_post_created` | (post_id, created_at) |
| `ix_post_revisions_author_id` | (author_id) |

### AdminAuditLog
| Name | Columns |
|------|---------|
| `ix_admin_audit_logs_actor_timestamp` | (actor_id, timestamp) |
| `ix_admin_audit_logs_action_timestamp` | (action, timestamp) |

## User Model Details

```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(64), nullable=True, unique=True)
    reset_token_expires_at = db.Column(UTCDateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(UTCDateTime, nullable=True)
    totp_secret_encrypted = db.Column(db.String(256), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # TOTP secret is accessed via property that decrypts on access:
    @property
    def totp_secret(self) -> Optional[str]: ...  # Decrypts from totp_secret_encrypted
    set_totp_secret(secret)                     # Encrypts for storage
    get_totp_uri()                              # Generate QR code provisioning URI
    backup_codes_hashed = db.Column(db.JSON, nullable=True)    # SHA-256 hashed backup codes

    # Relationships
    admin_sessions = db.relationship("AdminSession", back_populates="user")

    # Methods
    __repr__()  # Returns <User id={self.id}> (not username - for PII/security)
    set_password(password)
    check_password(password)
    is_locked()
    record_failed_login(max_attempts, lockout_minutes)
    reset_failed_login()
    generate_backup_codes()  # Returns 8 plain-text codes, stores SHA-256 hashes
    verify_backup_code(code)  # Single-use verification, removes hash on success
```

**Note**: The User model only has the `admin_sessions` relationship. Reverse lookups like `user.posts` or `user.audit_logs` do not exist. Post-User relationships are not currently implemented (Posts do not track their author via user_id). AdminAuditLog-User relationship is defined on the AdminAuditLog model via the `actor` relationship.

## AdminSession Model Details

```python
class AdminSession(db.Model):
    __tablename__ = "admin_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)
    last_activity = db.Column(UTCDateTime, default=utc_now)

    user = db.relationship("User", back_populates="admin_sessions")

    # Index: ix_admin_sessions_user_id
    __repr__()  # Returns <AdminSession user_id={self.user_id} ip={self.ip_address}>
```

Used for session tracking and IP binding verification.

## Webhook Model Details

```python
class Webhook(db.Model):
    __tablename__ = "webhooks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)  # AES-256-GCM encrypted
    event_type = db.Column(db.String(32), nullable=False)  # post.published, subscriber.confirmed, etc.
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    # Webhook secret is accessed via property that decrypts on access (similar to TOTP pattern):
    @property
    def secret(self) -> Optional[str]: ...  # Decrypts from webhook_secret_encrypted via AES-256-GCM
    @secret.setter
    def secret(self, value) -> None ...     # Encrypts for storage

    # Index: ix_webhooks_event_type_enabled
    __repr__()  # Returns <Webhook {name!r} event={event_type!r}>
```

## WebhookEvent Model Details

```python
class WebhookEvent(db.Model):
    __tablename__ = "webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhooks.id"), nullable=True)
    event_type = db.Column(db.String(32), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    target_type = db.Column(db.String(32), nullable=True)  # "post", "subscriber", etc.
    delivered = db.Column(db.Boolean, default=False, nullable=False)
    delivery_status = db.Column(db.String(32), nullable=True)  # 'delivered', 'partial_failure', 'failed'
    delivery_attempts = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    webhook = db.relationship("Webhook", lazy="select")

    # Indexes: ix_webhook_events_event_type_delivered, ix_webhook_events_webhook_id
    __repr__()  # Returns <WebhookEvent event={event_type!r} delivered={delivered}>
```

## Series Model Details

```python
class Series(db.Model):
    __tablename__ = "series"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), default="")
    image = db.Column(db.String(256))
    created_at = db.Column(UTCDateTime, default=utc_now)

    posts = db.relationship("PostSeries", back_populates="series", order_by="PostSeries.order_index")

    # Index: ix_series_slug
    @staticmethod
    def generate_slug(name: str) -> str  # Uses app.utils.generate_slug

    __repr__()  # Returns <Series {name!r}>
```

## PostSeries Model Details

```python
class PostSeries(db.Model):
    __tablename__ = "post_series"

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)

    series = db.relationship("Series", back_populates="posts")
    post = db.relationship("Post")

    # Indexes: ix_post_series_series_id, ix_post_series_post_id
    # UniqueConstraint: (series_id, post_id) named uq_series_post

    __repr__()  # Returns <PostSeries series={series_id} post={post_id}>
```

Junction table linking Series and Post with ordering support.

## Post Model Details

```python
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), unique=True)
    body = db.Column(db.Text)
    summary = db.Column(db.String(500))
    image = db.Column(db.String(256))  # Featured image
    image_alt_text = db.Column(db.String(256))
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(UTCDateTime)
    scheduled_publish_at = db.Column(UTCDateTime)
    newsletter_sent_at = db.Column(UTCDateTime)
    newsletter_attempts = db.Column(db.Integer, default=0)

    # Relationships
    tags = db.relationship("Tag", secondary=post_tags)
    page_views = db.relationship("PageView", cascade="all,delete-orphan")
    share_events = db.relationship("ShareEvent", cascade="all,delete-orphan")
    revisions = db.relationship("PostRevision", cascade="all,delete-orphan")
    series_entries = db.relationship("PostSeries", cascade="all,delete-orphan")
    comments = db.relationship("Comment", cascade="all,delete-orphan")
```

## Comment Model (Nested)

```python
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"))  # For nested replies
    author_name = db.Column(db.String(100))
    author_email = db.Column(db.String(256), nullable=False)  # Required field
    content = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)  # Moderation required
    is_spam = db.Column(db.Boolean, default=False, nullable=False)
    spam_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)

    # Self-referential relationship for replies
    parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
    replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

## Page Model Details

```python
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), unique=True)
    body = db.Column(db.Text)
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)
    published = db.Column(db.Boolean, default=False)

    # Index: ix_pages_published_slug
```

## SiteSettings

```python
THEME_PRESETS = {
    "github-dark": { ... },
    "github-light": { ... },
    "solarized-dark": { ... },
    "monokai": { ... },
}

class SiteSettings(db.Model):
    theme_preset = db.Column(db.String(32), default="github-dark")
    syntax_theme = db.Column(db.String(50), default="prism")
    custom_css_enabled = db.Column(db.Boolean, default=False)
    custom_css = db.Column(db.Text, default="")
    logo_text = db.Column(db.String(100), default="")
    updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)

    @classmethod
    def get_instance(cls) -> "SiteSettings":
        """Return singleton instance (id=1), creating if needed."""
        instance = db.session.get(cls, 1)
        if instance is None:
            instance = cls()
            db.session.add(instance)
            db.session.commit()
        return instance
```

## ApiToken Model Details

```python
class ApiToken(db.Model):
    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False)
    scopes = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(UTCDateTime, default=utc_now)
    last_used_at = db.Column(UTCDateTime, nullable=True)
    expires_at = db.Column(UTCDateTime, nullable=True)
    revoked_at = db.Column(UTCDateTime, nullable=True)

    # Indexes: ix_api_tokens_token_hash, ix_api_tokens_revoked_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
    def has_scope(self, scope: str) -> bool:
        """Check if token has the given scope. 'admin:*' matches all scopes."""

    __repr__()  # Returns <ApiToken id={self.id} name={self.name!r}>
```

## See Also
- [App Factory](core/app-factory.md) - Application initialization
- [Search](infrastructure/search.md) - FTS5 full-text search
