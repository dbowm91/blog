"""add_totp_secret_to_user

Revision ID: add_totp_secret_to_user
Revises: add_comment_model
Create Date: 2026-05-01

"""

from alembic import op
import sqlalchemy as sa

revision = "add_totp_secret_to_user"
down_revision = "add_comment_model"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("totp_secret", sa.String(32), nullable=True))


def downgrade():
    op.drop_column("users", "totp_secret")
