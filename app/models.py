import uuid
from datetime import timedelta

from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.base62 import encode
from app.utils import utc_now, UTCDateTime

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
    db.Index("ix_post_tags_tag_id", "tag_id"),
)


class User(UserMixin, db.Model):  # type: ignore[name-defined]
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(64), nullable=True, unique=True)
    reset_token_expires_at = db.Column(UTCDateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(UTCDateTime, nullable=True)
    totp_secret_encrypted = db.Column(db.String(256), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)

    admin_sessions = db.relationship(
        "AdminSession",
        back_populates="user",
        lazy="select",
        cascade="all,delete-orphan",
    )

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

    def set_totp_secret(self, secret: str) -> None:
        """Encrypt and store TOTP secret."""
        if not secret:
            self.totp_secret_encrypted = None
            return
        from app.services.encryption import encrypt

        self.totp_secret_encrypted = encrypt(secret)

    def get_totp_uri(self) -> Optional[str]:
        """Get TOTP provisioning URI for QR code."""
        secret = self.totp_secret
        if not secret:
            return None
        import pyotp

        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.username, issuer_name="DevLog Blog"
        )

    backup_codes_hashed = db.Column(db.JSON, nullable=True)

    def generate_backup_codes(self) -> list[str]:
        """Generate 8 backup codes, return plain codes (one-time display)."""
        import secrets

        codes = []
        for _ in range(8):
            code = f"{secrets.token_hex(4).upper()[:4]}-{secrets.token_hex(4).upper()[4:8]}"
            codes.append(code)
        import hashlib

        self.backup_codes_hashed = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
        return codes

    def verify_backup_code(self, code: str) -> bool:
        """Verify a backup code (single-use)."""
        import hashlib

        if not self.backup_codes_hashed:
            return False
        hashed = hashlib.sha256(code.encode()).hexdigest()
        if hashed in self.backup_codes_hashed:
            self.backup_codes_hashed.remove(hashed)
            return True
        return False

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return bool(check_password_hash(self.password_hash, password))

    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return bool(utc_now() < self.locked_until)

    def record_failed_login(self, max_attempts: int, lockout_minutes: int) -> None:
        """Record a failed login attempt."""
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = utc_now() + timedelta(minutes=lockout_minutes)

    def reset_failed_login(self) -> None:
        """Reset failed login counter on successful login."""
        self.failed_login_count = 0
        self.locked_until = None

    def __repr__(self) -> str:
        return f"<User id={self.id}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return db.session.get(User, int(user_id))


class Tag(db.Model):  # type: ignore[name-defined]
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags", lazy="select")

    @staticmethod
    def generate_slug(name: str) -> str:
        from app.utils import generate_slug as util_generate_slug

        return util_generate_slug(name)

    def __repr__(self) -> str:
        return f"<Tag {self.name!r}>"


class Page(db.Model):  # type: ignore[name-defined]
    __tablename__ = "pages"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    published = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.Index("ix_pages_published_slug", "published", "slug"),)

    @staticmethod
    def generate_slug(title: str) -> str:
        from app.utils import generate_slug as util_generate_slug

        return util_generate_slug(title)

    def __repr__(self) -> str:
        return f"<Page {self.title!r} published={self.published}>"


class Post(db.Model):  # type: ignore[name-defined]
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500), default="")
    image = db.Column(db.String(256), nullable=True)
    image_alt_text = db.Column(db.String(256), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(UTCDateTime, nullable=True)
    scheduled_publish_at = db.Column(UTCDateTime, nullable=True)
    newsletter_sent_at = db.Column(UTCDateTime, nullable=True)
    newsletter_attempts = db.Column(db.Integer, default=0, nullable=False)

    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    page_views = db.relationship(
        "PageView", back_populates="post", lazy="select", cascade="all, delete-orphan"
    )
    share_events = db.relationship(
        "ShareEvent", back_populates="post", lazy="select", cascade="all, delete-orphan"
    )
    revisions = db.relationship(
        "PostRevision", back_populates="post", lazy="select", cascade="all, delete-orphan"
    )
    series_entries = db.relationship(
        "PostSeries", back_populates="post", lazy="select", cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", back_populates="post", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index("ix_posts_published_created", "published", "created_at"),
        db.Index("ix_posts_published_at", "published_at"),
        db.Index("ix_posts_newsletter_sent_at", "newsletter_sent_at"),
        db.Index("ix_posts_published_updated", "published", "updated_at"),
        db.Index("ix_posts_published_slug", "published", "slug"),
        db.Index("ix_posts_scheduled_publish_at", "scheduled_publish_at"),
    )

    @staticmethod
    def generate_slug(title: str) -> str:
        from app.utils import generate_slug as util_generate_slug

        return util_generate_slug(title)

    def short_code(self) -> str:
        return encode(self.id)

    def __repr__(self) -> str:
        return f"<Post {self.title!r} published={self.published}>"


class PostRevision(db.Model):  # type: ignore[name-defined]
    __tablename__ = "post_revisions"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500), default="")
    created_at = db.Column(UTCDateTime, default=utc_now)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    post = db.relationship("Post", back_populates="revisions")
    author = db.relationship("User", lazy="select")

    __table_args__ = (
        db.Index("ix_post_revisions_post_created", "post_id", "created_at"),
        db.Index("ix_post_revisions_author_id", "author_id"),
    )

    def __repr__(self) -> str:
        return f"<PostRevision post_id={self.post_id} created_at={self.created_at}>"


class Subscriber(db.Model):  # type: ignore[name-defined]
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(UTCDateTime, default=utc_now)
    expires_at = db.Column(
        UTCDateTime,
        nullable=True,
        doc="Confirmation deadline. Subscribers removed if not confirmed before this time.",
    )
    unsubscribed_at = db.Column(UTCDateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_subscribers_confirmed_unsubscribed", "confirmed", "unsubscribed_at"),
    )

    def __repr__(self) -> str:
        return f"<Subscriber id={self.id} confirmed={self.confirmed}>"


class PageView(db.Model):  # type: ignore[name-defined]
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    referrer = db.Column(db.String(512), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)

    post = db.relationship("Post", back_populates="page_views")

    __table_args__ = (db.Index("ix_page_views_post_created", "post_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<PageView post_id={self.post_id}>"


class ShareEvent(db.Model):  # type: ignore[name-defined]
    __tablename__ = "share_events"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    post = db.relationship("Post", back_populates="share_events")

    __table_args__ = (
        db.Index("ix_share_events_post_created", "post_id", "created_at"),
        db.Index("ix_share_events_platform", "platform"),
    )

    def __repr__(self) -> str:
        return f"<ShareEvent post_id={self.post_id} platform={self.platform!r}>"


class AdminSession(db.Model):  # type: ignore[name-defined]
    __tablename__ = "admin_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)
    last_activity = db.Column(UTCDateTime, default=utc_now)

    user = db.relationship("User", back_populates="admin_sessions")

    __table_args__ = (db.Index("ix_admin_sessions_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<AdminSession user_id={self.user_id} ip={self.ip_address!r}>"


class SiteSettings(db.Model):  # type: ignore[name-defined]
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    theme_preset = db.Column(db.String(32), default="github-dark", nullable=False)
    syntax_theme = db.Column(db.String(50), default="prism", nullable=False)
    custom_css_enabled = db.Column(db.Boolean, default=False, nullable=False)
    custom_css = db.Column(db.Text, default="", nullable=False)
    logo_text = db.Column(db.String(100), default="", nullable=False)
    theme_dark_name = db.Column(db.String(128), nullable=False, default="Catppuccin Mocha")
    theme_light_name = db.Column(db.String(128), nullable=False, default="Catppuccin Latte")
    theme_default_scheme = db.Column(db.String(16), nullable=False, default="system")
    updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)

    @classmethod
    def get_instance(cls) -> "SiteSettings":
        instance = cls.query.filter_by(id=1).with_for_update().first()
        if instance is None:
            instance = cls()
            db.session.add(instance)
            db.session.flush()
        return instance

    def __repr__(self) -> str:
        return f"<SiteSettings preset={self.theme_preset!r} syntax={self.syntax_theme!r} dark={self.theme_dark_name!r} light={self.theme_light_name!r} scheme={self.theme_default_scheme!r}>"


THEME_PRESETS = {
    "github-dark": {
        "name": "GitHub Dark",
        "bg": "#0d1117",
        "bg-surface": "#161b22",
        "bg-elevated": "#1c2128",
        "border": "#30363d",
        "text": "#e6edf3",
        "text-muted": "#8b949e",
        "text-dim": "#7d8590",
        "text-dim-strong": "#9ca3af",
        "accent": "#58a6ff",
        "accent-hover": "#79c0ff",
        "accent-dim": "rgba(88, 166, 255, 0.1)",
        "green": "#3fb950",
        "green-dim": "rgba(63, 185, 80, 0.15)",
        "red": "#f85149",
        "red-dim": "rgba(248, 81, 73, 0.15)",
        "yellow": "#d29922",
        "purple": "#a371f7",
        "purple-dim": "rgba(163, 113, 247, 0.15)",
        "coral": "#f78166",
        "coral-dim": "rgba(247, 129, 102, 0.15)",
    },
    "github-light": {
        "name": "GitHub Light",
        "bg": "#f6f8fa",
        "bg-surface": "#ffffff",
        "bg-elevated": "#f0f2f5",
        "border": "#d0d7de",
        "text": "#1f2328",
        "text-muted": "#57606a",
        "text-dim": "#6e7781",
        "accent": "#0969da",
        "accent-hover": "#0550ae",
        "accent-dim": "rgba(9, 105, 218, 0.1)",
        "green": "#1a7f37",
        "green-dim": "rgba(26, 127, 55, 0.15)",
        "red": "#cf222e",
        "red-dim": "rgba(207, 34, 46, 0.15)",
        "yellow": "#9a6700",
        "purple": "#8250df",
        "purple-dim": "rgba(130, 80, 223, 0.15)",
        "coral": "#d4513d",
        "coral-dim": "rgba(212, 81, 61, 0.15)",
    },
    "solarized-dark": {
        "name": "Solarized Dark",
        "bg": "#002b36",
        "bg-surface": "#073642",
        "bg-elevated": "#094857",
        "border": "#586e75",
        "text": "#839496",
        "text-muted": "#586e75",
        "text-dim": "#657b83",
        "accent": "#268bd2",
        "accent-hover": "#1e86c8",
        "accent-dim": "rgba(38, 139, 210, 0.1)",
        "green": "#859900",
        "green-dim": "rgba(133, 153, 0, 0.15)",
        "red": "#dc322f",
        "red-dim": "rgba(220, 50, 47, 0.15)",
        "yellow": "#b58900",
        "purple": "#6c71c4",
        "purple-dim": "rgba(108, 113, 196, 0.15)",
        "coral": "#cb4b16",
        "coral-dim": "rgba(203, 75, 22, 0.15)",
    },
    "monokai": {
        "name": "Monokai",
        "bg": "#272822",
        "bg-surface": "#3e3d32",
        "bg-elevated": "#49483e",
        "border": "#75715e",
        "text": "#f8f8f2",
        "text-muted": "#a6a69c",
        "text-dim": "#8b8b7a",
        "accent": "#66d9ef",
        "accent-hover": "#a6e3e8",
        "accent-dim": "rgba(102, 217, 239, 0.1)",
        "green": "#a6e22e",
        "green-dim": "rgba(166, 226, 46, 0.15)",
        "red": "#f92672",
        "red-dim": "rgba(249, 38, 114, 0.15)",
        "yellow": "#e6db74",
        "yellow-dim": "rgba(230, 219, 116, 0.15)",
        "purple": "#ae81ff",
        "purple-dim": "rgba(174, 129, 255, 0.15)",
        "coral": "#fd971f",
        "coral-dim": "rgba(253, 151, 31, 0.15)",
    },
}


class AdminAuditLog(db.Model):  # type: ignore[name-defined]
    __tablename__ = "admin_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    target_type = db.Column(db.String(32), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(UTCDateTime, default=utc_now)

    actor = db.relationship("User", lazy="select")

    __table_args__ = (
        db.Index("ix_admin_audit_logs_actor_timestamp", "actor_id", "timestamp"),
        db.Index("ix_admin_audit_logs_action_timestamp", "action", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog action={self.action!r} actor={self.actor_id}>"


class Webhook(db.Model):  # type: ignore[name-defined]
    __tablename__ = "webhooks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)
    event_type = db.Column(db.String(32), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    __table_args__ = (db.Index("ix_webhooks_event_type_enabled", "event_type", "enabled"),)

    @property
    def secret(self) -> Optional[str]:
        """Get decrypted webhook secret."""
        if not self.webhook_secret_encrypted:
            return None
        from app.webhook_encryption import decrypt_webhook_secret

        try:
            return decrypt_webhook_secret(self.webhook_secret_encrypted.decode("utf-8"))
        except Exception:
            return None

    @secret.setter
    def secret(self, value: Optional[str]) -> None:
        """Encrypt and store webhook secret."""
        if not value:
            self.webhook_secret_encrypted = None
            return
        from app.webhook_encryption import encrypt_webhook_secret

        self.webhook_secret_encrypted = encrypt_webhook_secret(value).encode("utf-8")

    def __repr__(self) -> str:
        return f"<Webhook {self.name!r} event={self.event_type!r}>"


class WebhookEvent(db.Model):  # type: ignore[name-defined]
    __tablename__ = "webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhooks.id"), nullable=True)
    event_type = db.Column(db.String(32), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    target_type = db.Column(db.String(32), nullable=True)
    delivered = db.Column(db.Boolean, default=False, nullable=False)
    delivery_status = db.Column(db.String(32), nullable=True)
    delivery_attempts = db.Column(db.Integer, default=0, nullable=False)
    successful_deliveries = db.Column(db.Integer, default=0, nullable=False)
    failed_deliveries = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    webhook = db.relationship("Webhook", lazy="select")

    __table_args__ = (
        db.Index("ix_webhook_events_event_type_delivered", "event_type", "delivered"),
        db.Index("ix_webhook_events_webhook_id", "webhook_id"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent event={self.event_type!r} delivered={self.delivered}>"


class Series(db.Model):  # type: ignore[name-defined]
    __tablename__ = "series"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), default="")
    image = db.Column(db.String(256))
    created_at = db.Column(UTCDateTime, default=utc_now)

    posts = db.relationship(
        "PostSeries", back_populates="series", order_by="PostSeries.order_index"
    )

    __table_args__ = (db.Index("ix_series_slug", "slug"),)

    @staticmethod
    def generate_slug(name: str) -> str:
        from app.utils import generate_slug as util_generate_slug

        return util_generate_slug(name)

    def __repr__(self) -> str:
        return f"<Series {self.name!r}>"


class PostSeries(db.Model):  # type: ignore[name-defined]
    __tablename__ = "post_series"

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)

    series = db.relationship("Series", back_populates="posts")
    post = db.relationship("Post")

    __table_args__ = (
        db.Index("ix_post_series_series_id", "series_id"),
        db.Index("ix_post_series_post_id", "post_id"),
        db.UniqueConstraint("series_id", "post_id", name="uq_series_post"),
    )

    def __repr__(self) -> str:
        return f"<PostSeries series_id={self.series_id} post_id={self.post_id} order={self.order_index}>"


class Comment(db.Model):  # type: ignore[name-defined]
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    is_spam = db.Column(db.Boolean, default=False, nullable=False)
    spam_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)

    post = db.relationship("Post", back_populates="comments")
    parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
    replies = db.relationship("Comment", back_populates="parent", lazy="select")

    __table_args__ = (
        db.Index("ix_comments_post_approved", "post_id", "approved"),
        db.Index("ix_comments_created_at", "created_at"),
        db.Index("ix_comments_parent_id", "parent_id"),
        db.Index("ix_comments_is_spam", "is_spam"),
    )

    def __repr__(self) -> str:
        return f"<Comment post_id={self.post_id} approved={self.approved} is_spam={self.is_spam}>"


class ApiToken(db.Model):  # type: ignore[name-defined]
    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False)
    scopes = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(UTCDateTime, default=utc_now)
    last_used_at = db.Column(UTCDateTime, nullable=True)
    expires_at = db.Column(UTCDateTime, nullable=True)
    revoked_at = db.Column(UTCDateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_api_tokens_token_hash", "token_hash"),
        db.Index("ix_api_tokens_revoked_at", "revoked_at"),
    )

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and utc_now() > self.expires_at:
            return False
        return True

    def has_scope(self, scope: str) -> bool:
        """Check if token has the given scope.

        Supports exact match, ``admin:*`` global wildcard, and category
        wildcards (e.g. ``posts:*`` grants ``posts:read``).
        """
        from app.routes.api.auth import VALID_WILDCARD_SCOPES

        if "admin:*" in self.scopes:
            return True
        if scope in self.scopes:
            return True
        if ":" in scope:
            category = scope.split(":", 1)[0]
            wildcard = f"{category}:*"
            if wildcard in self.scopes and wildcard in VALID_WILDCARD_SCOPES:
                return True
        return False

    def __repr__(self) -> str:
        return f"<ApiToken id={self.id} name={self.name!r}>"
