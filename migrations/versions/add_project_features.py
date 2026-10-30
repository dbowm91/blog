"""add project feature entries

Revision ID: add_project_features
Revises: add_project_sync_leases
Create Date: 2026-10-30
"""

from alembic import op
import sqlalchemy as sa

revision = "add_project_features"
down_revision = "add_project_sync_leases"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("features", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("features")
