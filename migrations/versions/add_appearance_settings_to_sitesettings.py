"""add appearance settings to SiteSettings

Revision ID: add_appearance_settings_to_sitesettings
Revises: reconcile_schema_with_models
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa

revision = "add_appearance_settings_to_sitesettings"
down_revision = "reconcile_schema_with_models"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "font_sans",
                sa.String(length=128),
                nullable=False,
                server_default="inter",
            )
        )
        batch_op.add_column(
            sa.Column(
                "font_mono",
                sa.String(length=128),
                nullable=False,
                server_default="jetbrains-mono",
            )
        )
        batch_op.add_column(
            sa.Column(
                "backdrop",
                sa.String(length=128),
                nullable=False,
                server_default="default",
            )
        )


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("backdrop")
        batch_op.drop_column("font_mono")
        batch_op.drop_column("font_sans")
