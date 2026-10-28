"""add_projects_table

Revision ID: add_projects_table
Revises: drop_syntax_theme_column
Create Date: 2026-10-28

"""

from alembic import op
import sqlalchemy as sa

revision = "add_projects_table"
down_revision = "drop_syntax_theme_column"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repo_url", sa.String(length=512), nullable=True),
        sa.Column("landing_style", sa.String(length=32), nullable=False, server_default="minimal"),
        sa.Column("theme_dark_name", sa.String(length=128), nullable=True),
        sa.Column("theme_light_name", sa.String(length=128), nullable=True),
        sa.Column("show_in_nav", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nav_label", sa.String(length=120), nullable=True),
        sa.Column("hero_image", sa.String(length=256), nullable=True),
        sa.Column("hero_image_alt", sa.String(length=256), nullable=True),
        sa.Column("screenshots", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_projects_published_sort_title",
        "projects",
        ["published", "sort_order", "title"],
        unique=False,
    )
    op.create_index(
        "ix_projects_published_slug",
        "projects",
        ["published", "slug"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_projects_published_slug", table_name="projects")
    op.drop_index("ix_projects_published_sort_title", table_name="projects")
    op.drop_table("projects")
