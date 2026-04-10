"""Add site settings for theming

Revision ID: sitesettings
Revises: 1992db4c5c98
Create Date: 2026-04-10

"""

from alembic import op
import sqlalchemy as sa


revision = "sitesettings"
down_revision = "1992db4c5c98"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("theme_preset", sa.String(length=32), nullable=False),
        sa.Column("custom_css_enabled", sa.Boolean(), nullable=False),
        sa.Column("custom_css", sa.Text(), nullable=True),
        sa.Column("logo_text", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.insert(
        "site_settings",
        [
            {
                "id": 1,
                "theme_preset": "github-dark",
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
            }
        ],
    )


def downgrade():
    op.drop_table("site_settings")
