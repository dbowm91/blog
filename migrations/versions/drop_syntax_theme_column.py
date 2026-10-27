"""drop syntax_theme column from site_settings

Revision ID: drop_syntax_theme_column
Revises: add_appearance_settings_to_sitesettings
Create Date: 2026-10-27

"""

from alembic import op
import sqlalchemy as sa

revision = "drop_syntax_theme_column"
down_revision = "add_appearance_settings_to_sitesettings"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("syntax_theme")


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "syntax_theme",
                sa.String(length=50),
                nullable=False,
                server_default="prism",
            )
        )
