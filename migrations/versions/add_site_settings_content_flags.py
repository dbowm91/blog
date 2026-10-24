"""add_site_settings_content_flags

Revision ID: add_site_settings_content_flags
Revises: drop_theme_preset_column
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa

revision = "add_site_settings_content_flags"
down_revision = "drop_theme_preset_column"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "site_settings",
        sa.Column("comments_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "site_settings",
        sa.Column("footer_text", sa.String(300), server_default="", nullable=False),
    )
    op.add_column(
        "site_settings",
        sa.Column("footer_show_posts", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "site_settings",
        sa.Column("footer_show_tags", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade():
    op.drop_column("site_settings", "footer_show_tags")
    op.drop_column("site_settings", "footer_show_posts")
    op.drop_column("site_settings", "footer_text")
    op.drop_column("site_settings", "comments_enabled")
