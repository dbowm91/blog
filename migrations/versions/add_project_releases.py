"""add canonical GitHub release catalog

Revision ID: add_project_releases
Revises: add_project_github_docs_snapshots
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_releases"
down_revision = "add_project_github_docs_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("releases_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column(
                "releases_include_prereleases",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("releases_sync_status", sa.String(16), nullable=False, server_default="never")
        )
        batch_op.add_column(sa.Column("releases_sync_error", sa.String(500), nullable=True))
        batch_op.add_column(
            sa.Column("releases_synced_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("releases_etag", sa.String(256), nullable=True))
    op.create_table(
        "project_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_release_id", sa.String(32), nullable=False),
        sa.Column("tag_name", sa.String(256), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("notes_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("html_url", sa.String(1024), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prerelease", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "project_id", "provider_release_id", name="uq_project_release_provider_id"
        ),
    )
    op.create_index(
        "ix_project_releases_project_published", "project_releases", ["project_id", "published_at"]
    )
    op.create_table(
        "project_release_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "release_id",
            sa.Integer(),
            sa.ForeignKey("project_releases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_asset_id", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("browser_download_url", sa.String(1024), nullable=False),
        sa.Column("provider_digest", sa.String(128), nullable=True),
        sa.UniqueConstraint(
            "release_id", "provider_asset_id", name="uq_project_release_asset_provider_id"
        ),
    )


def downgrade():
    op.drop_table("project_release_assets")
    op.drop_index("ix_project_releases_project_published", table_name="project_releases")
    op.drop_table("project_releases")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("releases_etag")
        batch_op.drop_column("releases_synced_at")
        batch_op.drop_column("releases_sync_error")
        batch_op.drop_column("releases_sync_status")
        batch_op.drop_column("releases_include_prereleases")
        batch_op.drop_column("releases_enabled")
