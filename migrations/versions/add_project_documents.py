"""add local project documentation

Revision ID: add_project_documents
Revises: add_project_navigation_settings
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_documents"
down_revision = "add_project_navigation_settings"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("docs_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("docs_home_path", sa.String(512), nullable=True))
    op.create_table(
        "project_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_key", sa.String(64), nullable=False, server_default="current"),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("nav_title", sa.String(120), nullable=True),
        sa.Column("nav_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "project_id", "version_key", "path", name="uq_project_document_version_path"
        ),
    )
    op.create_index(
        "ix_project_documents_project_version_published_order",
        "project_documents",
        ["project_id", "version_key", "published", "nav_order"],
    )
    op.create_table(
        "project_document_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "path", name="uq_project_document_asset_path"),
    )
    op.create_index(
        "ix_project_document_assets_project_path",
        "project_document_assets",
        ["project_id", "path"],
    )


def downgrade():
    op.drop_index("ix_project_document_assets_project_path", table_name="project_document_assets")
    op.drop_table("project_document_assets")
    op.drop_index(
        "ix_project_documents_project_version_published_order", table_name="project_documents"
    )
    op.drop_table("project_documents")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("docs_home_path")
        batch_op.drop_column("docs_enabled")
