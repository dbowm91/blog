"""Add performance indexes for scheduled_publish_at and share_events platform

Revision ID: add_perf_indexes
Revises: sitesettings
Create Date: 2026-05-01

"""
from alembic import op
import sqlalchemy as sa

revision = "add_perf_indexes"
down_revision = "sitesettings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_posts_scheduled_publish_at', 'posts', ['scheduled_publish_at'], unique=False)
    op.create_index('ix_share_events_platform', 'share_events', ['platform'], unique=False)


def downgrade():
    op.drop_index('ix_share_events_platform', table_name='share_events')
    op.drop_index('ix_posts_scheduled_publish_at', table_name='posts')
