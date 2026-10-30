"""make the blueprint grid the default page backdrop

Revision ID: default_blueprint_grid_backdrop
Revises: add_project_features
Create Date: 2026-10-30

The bundled backdrops were reworked. The blueprint grid is the default, and
the graphics that used to carry the "default" and "waves" keys are gone. A
stored key that no longer resolves leaves the page with no backdrop at all,
because the appearance service reports an unknown key as missing rather than
falling back, so every stored value is moved onto the new default.

The downgrade restores the old server default. It cannot restore which of the
two legacy keys a row held, so those rows come back as "default".
"""

from alembic import op
import sqlalchemy as sa

revision = "default_blueprint_grid_backdrop"
down_revision = "add_project_features"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "backdrop",
            existing_type=sa.String(length=128),
            existing_nullable=False,
            existing_server_default="default",
            server_default="grid",
        )
    op.execute(
        sa.text("UPDATE site_settings SET backdrop = 'grid' WHERE backdrop IN ('default', 'waves')")
    )


def downgrade():
    op.execute(sa.text("UPDATE site_settings SET backdrop = 'default' WHERE backdrop = 'grid'"))
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "backdrop",
            existing_type=sa.String(length=128),
            existing_nullable=False,
            existing_server_default="grid",
            server_default="default",
        )
