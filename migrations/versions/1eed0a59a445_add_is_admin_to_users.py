"""add is_admin to users

Revision ID: 1eed0a59a445
Revises: 89a922eae517
Create Date: 2026-03-31 03:54:37.103828

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1eed0a59a445'
down_revision = '89a922eae517'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'is_admin')
