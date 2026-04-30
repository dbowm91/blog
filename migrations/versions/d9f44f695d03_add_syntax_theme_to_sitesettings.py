"""add syntax_theme to SiteSettings

Revision ID: d9f44f695d03
Revises: a6d90d923ef2
Create Date: 2026-04-30 22:55:38.447211

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9f44f695d03'
down_revision = 'a6d90d923ef2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('syntax_theme', sa.String(length=50), nullable=False, server_default='prism'))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('syntax_theme')
