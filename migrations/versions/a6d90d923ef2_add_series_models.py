"""add series models

Revision ID: a6d90d923ef2
Revises: 3328a74db69b
Create Date: 2026-04-30 19:29:13.445553

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a6d90d923ef2"
down_revision = "3328a74db69b"
branch_labels = None
depends_on = None


def upgrade():
    # Check if series table already exists
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "series" not in tables:
        op.create_table(
            "series",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("image", sa.String(length=256), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        with op.batch_alter_table("series", schema=None) as batch_op:
            batch_op.create_index("ix_series_slug", ["slug"], unique=False)

    if "post_series" not in tables:
        op.create_table(
            "post_series",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("series_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.ForeignKeyConstraint(["series_id"], ["series.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("series_id", "post_id", name="uq_series_post"),
        )
        with op.batch_alter_table("post_series", schema=None) as batch_op:
            batch_op.create_index("ix_post_series_post_id", ["post_id"], unique=False)
            batch_op.create_index("ix_post_series_series_id", ["series_id"], unique=False)


def downgrade():
    # Check if tables exist before dropping
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "post_series" in tables:
        with op.batch_alter_table("post_series", schema=None) as batch_op:
            batch_op.drop_index("ix_post_series_series_id")
            batch_op.drop_index("ix_post_series_post_id")
        op.drop_table("post_series")

    if "series" in tables:
        with op.batch_alter_table("series", schema=None) as batch_op:
            batch_op.drop_index("ix_series_slug")
        op.drop_table("series")
