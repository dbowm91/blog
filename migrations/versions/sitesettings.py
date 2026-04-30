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
    # Check if table already exists (might exist from manual creation)
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if "site_settings" not in tables:
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
        # Insert default site settings row
        op.execute(
            text(
                """
                INSERT INTO site_settings (id, theme_preset, custom_css_enabled, custom_css, logo_text)
                VALUES (1, 'github-dark', 0, '', '')
                """
            )
        )


def downgrade():
    op.drop_table("site_settings")
