"""add_post_revisions

Revision ID: add_post_revisions
Revises: 1eed0a59a445
Create Date: 2026-04-21

"""

from alembic import op
import sqlalchemy as sa

revision = "add_post_revisions"
down_revision = "1eed0a59a445"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer, sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("summary", sa.String(500), default=""),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_post_revisions_post_created", "post_revisions", ["post_id", "created_at"])


def downgrade():
    op.drop_index("ix_post_revisions_post_created", table_name="post_revisions")
    op.drop_table("post_revisions")
