"""add_webhook_event_delivery_status

Revision ID: add_webhook_event_delivery_status
Revises: add_webhook_secret_encryption
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_webhook_event_delivery_status'
down_revision = 'add_webhook_secret_encryption'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'webhook_events',
        sa.Column('delivery_status', sa.String(32), nullable=True)
    )


def downgrade():
    op.drop_column('webhook_events', 'delivery_status')