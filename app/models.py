import uuid
from datetime import datetime

from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.base62 import encode
from app.utils import generate_slug, utc_now, UTCDateTime

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username!r} admin={self.is_admin}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return db.session.get(User, int(user_id))


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    @staticmethod
    def generate_slug(name: str) -> str:
        return generate_slug(name)

    def __repr__(self) -> str:
        return f"<Tag {self.name!r}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500), default="")
    image = db.Column(db.String(256), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(UTCDateTime, nullable=True)
    scheduled_publish_at = db.Column(UTCDateTime, nullable=True)
    newsletter_sent_at = db.Column(UTCDateTime, nullable=True)
    newsletter_attempts = db.Column(db.Integer, default=0, nullable=False)

    tags = db.relationship("Tag", secondary=post_tags, backref=db.backref("posts", lazy="dynamic"))
    page_views = db.relationship("PageView", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    share_events = db.relationship("ShareEvent", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_posts_published_created", "published", "created_at"),
        db.Index("ix_posts_published_at", "published_at"),
        db.Index("ix_posts_newsletter_sent_at", "newsletter_sent_at"),
        db.Index("ix_posts_published_updated", "published", "updated_at"),
    )

    @staticmethod
    def generate_slug(title: str) -> str:
        return generate_slug(title)

    def short_code(self) -> str:
        return encode(self.id)

    def __repr__(self) -> str:
        return f"<Post {self.title!r} published={self.published}>"


class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(UTCDateTime, default=utc_now)
    expires_at = db.Column(
        UTCDateTime, nullable=True,
        doc="Confirmation deadline. Subscribers removed if not confirmed before this time.",
    )
    unsubscribed_at = db.Column(UTCDateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_subscribers_confirmed_unsubscribed", "confirmed", "unsubscribed_at"),
    )

    def __repr__(self) -> str:
        return f"<Subscriber {self.email!r} confirmed={self.confirmed}>"


class PageView(db.Model):
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    referrer = db.Column(db.String(512), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_page_views_post_created", "post_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PageView post_id={self.post_id}>"


class ShareEvent(db.Model):
    __tablename__ = "share_events"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_share_events_post_created", "post_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ShareEvent post_id={self.post_id} platform={self.platform!r}>"


class AdminSession(db.Model):
    __tablename__ = "admin_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    created_at = db.Column(UTCDateTime, default=utc_now)
    last_activity = db.Column(UTCDateTime, default=utc_now)

    user = db.relationship("User", backref=db.backref("admin_sessions", lazy="dynamic"))

    __table_args__ = (
        db.Index("ix_admin_sessions_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<AdminSession user_id={self.user_id} ip={self.ip_address!r}>"
