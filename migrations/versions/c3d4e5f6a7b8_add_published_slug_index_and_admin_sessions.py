"""add published_slug index and admin_sessions table

Revision ID: c3d4e5f6a7b8
Revises: 89a922eae517
Create Date: 2026-04-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = '89a922eae517'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check and create index on posts if not exists
    indexes = [idx['name'] for idx in inspector.get_indexes('posts')]
    if 'ix_posts_published_slug' not in indexes:
        with op.batch_alter_table('posts', schema=None) as batch_op:
            batch_op.create_index('ix_posts_published_slug', ['published', 'slug'], unique=False)
    
    # Check and create admin_sessions table if not exists
    tables = inspector.get_table_names()
    if 'admin_sessions' not in tables:
        op.create_table('admin_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.String(64), nullable=False),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(256), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_activity', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('session_id'),
        )
        op.create_index('ix_admin_sessions_user_id', 'admin_sessions', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_admin_sessions_user_id', table_name='admin_sessions')
    op.drop_table('admin_sessions')

    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_index('ix_posts_published_slug')
