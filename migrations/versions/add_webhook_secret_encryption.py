"""add_webhook_secret_encryption

Revision ID: add_webhook_secret_encryption
Revises: c3d4e5f6a7b8
Create Date: 2026-05-21

"""

from alembic import op
import sqlalchemy as sa


revision = "add_webhook_secret_encryption"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "webhooks", sa.Column("webhook_secret_encrypted", sa.LargeBinary(256), nullable=True)
    )


def downgrade():
    op.drop_column("webhooks", "webhook_secret_encrypted")
