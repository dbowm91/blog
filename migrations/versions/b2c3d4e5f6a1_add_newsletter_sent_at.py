"""add newsletter_sent_at to posts

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-25

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("newsletter_sent_at", sa.DateTime, nullable=True))


def downgrade():
    op.drop_column("posts", "newsletter_sent_at")
