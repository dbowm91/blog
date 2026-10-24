"""add_page_menu_fields

Revision ID: add_page_menu_fields
Revises: add_post_author
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa

revision = "add_page_menu_fields"
down_revision = "add_post_author"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pages",
        sa.Column("show_in_menu", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "site_settings",
        sa.Column("show_pages_in_menu", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "site_settings",
        sa.Column("menu_pages", sa.Text(), server_default="", nullable=False),
    )


def downgrade():
    op.drop_column("site_settings", "menu_pages")
    op.drop_column("site_settings", "show_pages_in_menu")
    op.drop_column("pages", "show_in_menu")
