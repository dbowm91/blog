"""add_post_author

Revision ID: add_post_author
Revises: add_user_profile_fields
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa

revision = "add_post_author"
down_revision = "add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("author_id", sa.Integer(), nullable=True))
    op.create_index("ix_posts_author_id", "posts", ["author_id"])

    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_posts_author_id_users",
            "posts",
            "users",
            ["author_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        sa.text(
            "UPDATE posts SET author_id = "
            "(SELECT MIN(id) FROM users WHERE is_admin = 1) "
            "WHERE author_id IS NULL "
            "AND EXISTS (SELECT 1 FROM users WHERE is_admin = 1)"
        )
    )


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_posts_author_id_users", "posts", type_="foreignkey")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_column("posts", "author_id")
