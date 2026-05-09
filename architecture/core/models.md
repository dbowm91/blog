# Database Models (`app/models.py`)

The blog uses SQLAlchemy ORM with the following models:

## Model Overview

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | Admin users | username, password_hash, totp_secret |
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
| `Webhook` | Webhook endpoints | name, url, secret, event_type |
| `WebhookEvent` | Webhook deliveries | event_type, payload, delivered |
| `Series` | Post series | name, slug, description |
| `PostSeries` | Series-post mapping | series_id, post_id, order_index |
| `Comment` | Post comments | post_id, parent_id, author_name, content |

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
└── user (reverse lookup: Post.user_id -> User.id)

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

### Tags
| Name | Columns |
|------|---------|
| `ix_post_tags_tag_id` | (tag_id) |

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
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(64), unique=True)
    reset_token_expires_at = db.Column(UTCDateTime)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(UTCDateTime)  # Account lockout
    totp_secret_encrypted = db.Column(db.String(256), nullable=True)  # Encrypted storage
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # TOTP secret is accessed via property that decrypts on access:
    @property
    def totp_secret(self) -> Optional[str]: ...  # Decrypts from totp_secret_encrypted
    set_totp_secret(secret)                     # Encrypts for storage
    get_totp_uri()                              # Generate QR code provisioning URI
    backup_codes_hashed = db.Column(db.JSON)    # SHA-256 hashed backup codes

    # Relationships
    admin_sessions = db.relationship("AdminSession", back_populates="user")

    # Methods
    __repr__()  # Returns <User id={self.id}> (not username - for PII/security)
    set_password(password)
    check_password(password)
    is_locked()
    record_failed_login(max_attempts, lockout_minutes)
    reset_failed_login()
```

**Note**: The User model only has the `admin_sessions` relationship. Reverse lookups like `user.posts` or `user.audit_logs` do not exist. Post-User relationships are defined on the Post model (e.g., `Post.user_id`). AdminAuditLog-User relationship is defined on the AdminAuditLog model.

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
    author_email = db.Column(db.String(256))
    content = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)  # Moderation required

    # Self-referential relationship for replies
    parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
    replies = db.relationship("Comment", back_populates="parent", lazy="select")
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

## See Also
- [App Factory](core/app-factory.md) - Application initialization
- [Search](infrastructure/search.md) - FTS5 full-text search
