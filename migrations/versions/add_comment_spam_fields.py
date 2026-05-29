"""Add is_spam and spam_score to comments.

Revision ID: add_comment_spam_fields
Revises: add_webhook_event_delivery_status
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "add_comment_spam_fields"
down_revision = "add_webhook_event_delivery_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("is_spam", sa.Boolean, nullable=False, server_default="0")
    )
    op.add_column(
        "comments",
        sa.Column("spam_score", sa.Float, nullable=True)
    )
    op.create_index(
        "ix_comments_is_spam",
        "comments",
        ["is_spam"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_comments_is_spam", table_name="comments")
    op.drop_column("comments", "spam_score")
    op.drop_column("comments", "is_spam")
