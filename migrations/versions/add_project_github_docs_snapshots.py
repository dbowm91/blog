"""add GitHub documentation source and snapshots

Revision ID: add_project_github_docs_snapshots
Revises: add_project_documents
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_github_docs_snapshots"
down_revision = "add_project_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_docs_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_ref", sa.String(256), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("etag", sa.String(256), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.UniqueConstraint("project_id", "commit_sha", name="uq_project_docs_snapshot_commit"),
    )
    op.create_index(
        "ix_project_docs_snapshots_project_status",
        "project_docs_snapshots",
        ["project_id", "status"],
    )
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("docs_source_kind", sa.String(16), nullable=False, server_default="local")
        )
        batch_op.add_column(sa.Column("github_owner", sa.String(39), nullable=True))
        batch_op.add_column(sa.Column("github_repository", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("github_docs_ref", sa.String(256), nullable=True))
        batch_op.add_column(
            sa.Column("github_docs_root", sa.String(512), nullable=False, server_default="docs")
        )
        batch_op.add_column(sa.Column("active_docs_snapshot_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("docs_sync_status", sa.String(16), nullable=False, server_default="never")
        )
        batch_op.add_column(sa.Column("docs_sync_error", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("docs_synced_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("project_documents") as batch_op:
        batch_op.add_column(sa.Column("snapshot_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_project_documents_snapshot_id",
            "project_docs_snapshots",
            ["snapshot_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade():
    with op.batch_alter_table("project_documents") as batch_op:
        batch_op.drop_constraint("fk_project_documents_snapshot_id", type_="foreignkey")
        batch_op.drop_column("snapshot_id")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("docs_synced_at")
        batch_op.drop_column("docs_sync_error")
        batch_op.drop_column("docs_sync_status")
        batch_op.drop_column("active_docs_snapshot_id")
        batch_op.drop_column("github_docs_root")
        batch_op.drop_column("github_docs_ref")
        batch_op.drop_column("github_repository")
        batch_op.drop_column("github_owner")
        batch_op.drop_column("docs_source_kind")
    op.drop_index("ix_project_docs_snapshots_project_status", table_name="project_docs_snapshots")
    op.drop_table("project_docs_snapshots")
