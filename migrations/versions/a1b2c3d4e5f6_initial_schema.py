"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(80), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("summary", sa.String(500), default=""),
        sa.Column("image", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("published", sa.Boolean, default=False),
        sa.Column("published_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_posts_published_created", "posts", ["published", "created_at"])
    op.create_index("ix_posts_slug", "posts", ["slug"])
    op.create_table(
        "post_tags",
        sa.Column("post_id", sa.Integer, sa.ForeignKey("posts.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), primary_key=True),
    )
    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(256), unique=True, nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("confirmed", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "page_views",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer, sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "share_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer, sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade():
    op.drop_table("share_events")
    op.drop_table("page_views")
    op.drop_table("subscribers")
    op.drop_table("post_tags")
    op.drop_index("ix_posts_slug", table_name="posts")
    op.drop_index("ix_posts_published_created", table_name="posts")
    op.drop_table("posts")
    op.drop_table("tags")
    op.drop_table("users")
