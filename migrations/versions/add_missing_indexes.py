"""add_missing_indexes

Revision ID: add_missing_indexes
Revises: 82ce77695033
Create Date: 2026-05-04

"""

from alembic import op
from sqlalchemy import inspect

revision = "add_missing_indexes"
down_revision = "82ce77695033"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("webhook_events")]
    if "ix_webhook_events_webhook_id" not in existing_indexes:
        with op.batch_alter_table("webhook_events", schema=None) as batch_op:
            batch_op.create_index("ix_webhook_events_webhook_id", ["webhook_id"], unique=False)

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("comments")]
    if "ix_comments_parent_id" not in existing_indexes:
        with op.batch_alter_table("comments", schema=None) as batch_op:
            batch_op.create_index("ix_comments_parent_id", ["parent_id"], unique=False)


def downgrade():
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_index("ix_comments_parent_id")
    with op.batch_alter_table("webhook_events", schema=None) as batch_op:
        batch_op.drop_index("ix_webhook_events_webhook_id")
