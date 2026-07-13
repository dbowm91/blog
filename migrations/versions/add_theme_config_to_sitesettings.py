"""add theme config columns to SiteSettings

Revision ID: add_theme_config_to_sitesettings
Revises: 3328a74db69b
Create Date: 2026-07-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_theme_config_to_sitesettings"
down_revision = "3328a74db69b"
branch_labels = None
depends_on = None

PRESET_MAP = {
    "github-dark": {"dark": "Catppuccin Mocha"},
    "github-light": {"light": "Catppuccin Latte"},
    "solarized-dark": {"dark": "Solarized Dark"},
    "monokai": {"dark": "Sonokai"},
}

DARK_PRESETS = {"github-dark", "solarized-dark", "monokai"}
LIGHT_PRESETS = {"github-light"}


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "theme_dark_name",
                sa.String(length=128),
                nullable=False,
                server_default="Catppuccin Mocha",
            )
        )
        batch_op.add_column(
            sa.Column(
                "theme_light_name",
                sa.String(length=128),
                nullable=False,
                server_default="Catppuccin Latte",
            )
        )
        batch_op.add_column(
            sa.Column(
                "theme_default_scheme",
                sa.String(length=16),
                nullable=False,
                server_default="system",
            )
        )

    op.execute(
        sa.text(
            "UPDATE site_settings SET "
            "theme_dark_name = CASE "
            "WHEN theme_preset = 'github-dark' THEN 'Catppuccin Mocha' "
            "WHEN theme_preset = 'solarized-dark' THEN 'Solarized Dark' "
            "WHEN theme_preset = 'monokai' THEN 'Sonokai' "
            "ELSE theme_dark_name END, "
            "theme_light_name = CASE "
            "WHEN theme_preset = 'github-light' THEN 'Catppuccin Latte' "
            "ELSE theme_light_name END"
        )
    )


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("theme_default_scheme")
        batch_op.drop_column("theme_light_name")
        batch_op.drop_column("theme_dark_name")
