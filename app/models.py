import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.base62 import encode
from app.utils import generate_slug, utc_now

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username!r}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    @staticmethod
    def generate_slug(name):
        return generate_slug(name)

    def __repr__(self):
        return f"<Tag {self.name!r}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500), default="")
    image = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    newsletter_sent_at = db.Column(db.DateTime, nullable=True)
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
    def generate_slug(title):
        return generate_slug(title)

    def short_code(self):
        return encode(self.id)

    def __repr__(self):
        return f"<Post {self.title!r} published={self.published}>"


class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    expires_at = db.Column(
        db.DateTime, nullable=True,
        doc="Confirmation deadline. Subscribers removed if not confirmed before this time.",
    )
    unsubscribed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_subscribers_confirmed_unsubscribed", "confirmed", "unsubscribed_at"),
    )

    def __repr__(self):
        return f"<Subscriber {self.email!r} confirmed={self.confirmed}>"


class PageView(db.Model):
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    referrer = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_page_views_post_created", "post_id", "created_at"),
    )

    def __repr__(self):
        return f"<PageView post_id={self.post_id}>"


class ShareEvent(db.Model):
    __tablename__ = "share_events"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_share_events_post_created", "post_id", "created_at"),
    )

    def __repr__(self):
        return f"<ShareEvent post_id={self.post_id} platform={self.platform!r}>"
