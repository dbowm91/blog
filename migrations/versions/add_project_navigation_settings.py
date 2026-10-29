"""add project navigation and homepage settings

Revision ID: add_project_navigation_settings
Revises: add_projects_table
Create Date: 2026-10-28

"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_navigation_settings"
down_revision = "add_projects_table"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "show_projects_in_menu",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "projects_menu_label",
                sa.String(length=64),
                nullable=False,
                server_default="Projects",
            )
        )
        batch_op.add_column(
            sa.Column(
                "homepage_kind",
                sa.String(length=16),
                nullable=False,
                server_default="blog",
            )
        )
        batch_op.add_column(
            sa.Column(
                "homepage_target_id",
                sa.Integer(),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("homepage_target_id")
        batch_op.drop_column("homepage_kind")
        batch_op.drop_column("projects_menu_label")
        batch_op.drop_column("show_projects_in_menu")
