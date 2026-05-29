"""Add composite indexes and published_at index

Revision ID: 1992db4c5c98
Revises: 656813f051c8
Create Date: 2026-03-30 04:23:16.100176

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "1992db4c5c98"
down_revision = "656813f051c8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_page_views_post_created",
        "page_views",
        ["post_id", "created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_share_events_post_created",
        "share_events",
        ["post_id", "created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_posts_published_at", "posts", ["published_at"], unique=False, if_not_exists=True
    )


def downgrade():
    op.drop_index("ix_posts_published_at", table_name="posts", if_exists=True)
    op.drop_index("ix_share_events_post_created", table_name="share_events", if_exists=True)
    op.drop_index("ix_page_views_post_created", table_name="page_views", if_exists=True)
