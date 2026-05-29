"""add_comment_model

Revision ID: add_comment_model
Revises: 3328a74db69b
Create Date: 2026-05-01

"""

from alembic import op
import sqlalchemy as sa

revision = "add_comment_model"
down_revision = "3328a74db69b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer, sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("comments.id"), nullable=True),
        sa.Column("author_name", sa.String(100), nullable=False),
        sa.Column("author_email", sa.String(256), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("approved", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_comments_post_approved", "comments", ["post_id", "approved"])
    op.create_index("ix_comments_created_at", "comments", ["created_at"])


def downgrade():
    op.drop_index("ix_comments_created_at", table_name="comments")
    op.drop_index("ix_comments_post_approved", table_name="comments")
    op.drop_table("comments")
