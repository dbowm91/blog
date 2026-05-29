"""Add referrer column to PageView

Revision ID: f439f3e05654
Revises: b2c3d4e5f6a1
Create Date: 2026-03-25 22:13:24.553641

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f439f3e05654"
down_revision = "b2c3d4e5f6a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("page_views", sa.Column("referrer", sa.String(512), nullable=True))


def downgrade():
    op.drop_column("page_views", "referrer")
