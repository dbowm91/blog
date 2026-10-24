"""add_user_profile_fields

Revision ID: add_user_profile_fields
Revises: add_site_settings_content_flags
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa

revision = "add_user_profile_fields"
down_revision = "add_site_settings_content_flags"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("display_name", sa.String(120), server_default="", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("bio_short", sa.String(300), server_default="", nullable=False),
    )
    op.add_column("users", sa.Column("bio_full", sa.Text(), server_default="", nullable=False))
    op.add_column("users", sa.Column("avatar_path", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("users", "avatar_path")
    op.drop_column("users", "bio_full")
    op.drop_column("users", "bio_short")
    op.drop_column("users", "display_name")
