"""add project synchronization leases and release sync configuration

Revision ID: add_project_sync_leases
Revises: add_project_releases
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_sync_leases"
down_revision = "add_project_releases"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("docs_sync_lease_owner", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("docs_sync_lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("releases_sync_lease_owner", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("releases_sync_lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("releases_sync_config", sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("releases_sync_config")
        batch_op.drop_column("releases_sync_lease_expires_at")
        batch_op.drop_column("releases_sync_lease_owner")
        batch_op.drop_column("docs_sync_lease_expires_at")
        batch_op.drop_column("docs_sync_lease_owner")
