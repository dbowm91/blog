"""drop theme_preset column from site_settings

Revision ID: drop_theme_preset_column
Revises: add_comment_spam_fields, add_missing_indexes, preserve_legacy_scheme
Create Date: 2026-07-14

"""

from alembic import op
import sqlalchemy as sa

revision = "drop_theme_preset_column"
down_revision = ("add_comment_spam_fields", "add_missing_indexes", "preserve_legacy_scheme")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("theme_preset")


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "theme_preset",
                sa.String(length=32),
                nullable=False,
                server_default="github-dark",
            )
        )
