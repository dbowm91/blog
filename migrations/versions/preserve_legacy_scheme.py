"""preserve legacy theme_default_scheme from old preset

Revision ID: preserve_legacy_scheme
Revises: add_theme_config_to_sitesettings
Create Date: 2026-07-14 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "preserve_legacy_scheme"
down_revision = "add_theme_config_to_sitesettings"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE site_settings SET theme_default_scheme = 'dark' "
            "WHERE theme_preset IN ('github-dark', 'solarized-dark', 'monokai') "
            "AND theme_default_scheme = 'system'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE site_settings SET theme_default_scheme = 'light' "
            "WHERE theme_preset = 'github-light' "
            "AND theme_default_scheme = 'system'"
        )
    )


def downgrade():
    op.execute(sa.text("UPDATE site_settings SET theme_default_scheme = 'system'"))
