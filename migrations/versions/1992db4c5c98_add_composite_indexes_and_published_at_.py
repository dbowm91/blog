"""Add composite indexes and published_at index

Revision ID: 1992db4c5c98
Revises: 656813f051c8
Create Date: 2026-03-30 04:23:16.100176

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1992db4c5c98'
down_revision = '656813f051c8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('page_views', schema=None) as batch_op:
        batch_op.drop_index('ix_page_views_post_id')
        batch_op.drop_index('ix_page_views_created_at')
        batch_op.create_index('ix_page_views_post_created', ['post_id', 'created_at'], unique=False)

    with op.batch_alter_table('share_events', schema=None) as batch_op:
        batch_op.create_index('ix_share_events_post_created', ['post_id', 'created_at'], unique=False)

    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.create_index('ix_posts_published_at', ['published_at'], unique=False)


def downgrade():
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_index('ix_posts_published_at')

    with op.batch_alter_table('share_events', schema=None) as batch_op:
        batch_op.drop_index('ix_share_events_post_created')

    with op.batch_alter_table('page_views', schema=None) as batch_op:
        batch_op.drop_index('ix_page_views_post_created')
        batch_op.create_index('ix_page_views_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_page_views_post_id', ['post_id'], unique=False)
