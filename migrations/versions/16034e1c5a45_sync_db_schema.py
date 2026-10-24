"""Sync database schema with models

Revision ID: 16034e1c5a45
Revises: d9f44f695d03
Create Date: 2026-05-01 04:05:00.000000

The DDL in this revision is conditional. It sits on one of the two branches
that leave ``1992db4c5c98``, and the other branch creates some of the same
objects: ``89a922eae517`` adds ``posts.newsletter_attempts`` and
``add_post_revisions`` creates the ``post_revisions`` table. A database built
from scratch runs both branches, so whichever branch arrives first creates the
object and this revision must not create it a second time.

A database that already has this revision applied is unaffected. The checks
find every object in place and change nothing.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "16034e1c5a45"
down_revision = "d9f44f695d03"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def _has_index(table: str, index: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return any(idx["name"] == index for idx in inspector.get_indexes(table))


def upgrade():
    if not _has_column("posts", "image_alt_text"):
        with op.batch_alter_table("posts", schema=None) as batch_op:
            batch_op.add_column(sa.Column("image_alt_text", sa.String(length=256), nullable=True))

    if not _has_column("posts", "newsletter_attempts"):
        with op.batch_alter_table("posts", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("newsletter_attempts", sa.Integer(), nullable=False, server_default="0")
            )

    if not _has_table("pages"):
        op.create_table(
            "pages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("slug", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("published", sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
    if not _has_index("pages", "ix_pages_published_slug"):
        op.create_index("ix_pages_published_slug", "pages", ["published", "slug"], unique=False)

    if not _has_table("webhooks"):
        op.create_table(
            "webhooks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=512), nullable=False),
            sa.Column("secret", sa.String(length=64), nullable=False),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("webhooks", "ix_webhooks_event_type_enabled"):
        op.create_index(
            "ix_webhooks_event_type_enabled", "webhooks", ["event_type", "enabled"], unique=False
        )

    if not _has_table("admin_audit_logs"):
        op.create_table(
            "admin_audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("target_type", sa.String(length=32), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("admin_audit_logs", "ix_admin_audit_logs_action_timestamp"):
        op.create_index(
            "ix_admin_audit_logs_action_timestamp",
            "admin_audit_logs",
            ["action", "timestamp"],
            unique=False,
        )
    if not _has_index("admin_audit_logs", "ix_admin_audit_logs_actor_timestamp"):
        op.create_index(
            "ix_admin_audit_logs_actor_timestamp",
            "admin_audit_logs",
            ["actor_id", "timestamp"],
            unique=False,
        )

    if not _has_table("post_revisions"):
        op.create_table(
            "post_revisions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("slug", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("summary", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("author_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("post_revisions", "ix_post_revisions_author_id"):
        op.create_index(
            "ix_post_revisions_author_id", "post_revisions", ["author_id"], unique=False
        )
    if not _has_index("post_revisions", "ix_post_revisions_post_created"):
        op.create_index(
            "ix_post_revisions_post_created",
            "post_revisions",
            ["post_id", "created_at"],
            unique=False,
        )

    if not _has_table("webhook_events"):
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("webhook_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("target_type", sa.String(length=32), nullable=True),
            sa.Column("delivered", sa.Boolean(), nullable=False),
            sa.Column("delivery_attempts", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("webhook_events", "ix_webhook_events_event_type_delivered"):
        op.create_index(
            "ix_webhook_events_event_type_delivered",
            "webhook_events",
            ["event_type", "delivered"],
            unique=False,
        )


def downgrade():
    if _has_index("webhook_events", "ix_webhook_events_event_type_delivered"):
        op.drop_index("ix_webhook_events_event_type_delivered", table_name="webhook_events")
    if _has_table("webhook_events"):
        op.drop_table("webhook_events")

    if _has_index("post_revisions", "ix_post_revisions_post_created"):
        op.drop_index("ix_post_revisions_post_created", table_name="post_revisions")
    if _has_index("post_revisions", "ix_post_revisions_author_id"):
        op.drop_index("ix_post_revisions_author_id", table_name="post_revisions")
    if _has_table("post_revisions"):
        op.drop_table("post_revisions")

    if _has_index("admin_audit_logs", "ix_admin_audit_logs_actor_timestamp"):
        op.drop_index("ix_admin_audit_logs_actor_timestamp", table_name="admin_audit_logs")
    if _has_index("admin_audit_logs", "ix_admin_audit_logs_action_timestamp"):
        op.drop_index("ix_admin_audit_logs_action_timestamp", table_name="admin_audit_logs")
    if _has_table("admin_audit_logs"):
        op.drop_table("admin_audit_logs")

    if _has_index("webhooks", "ix_webhooks_event_type_enabled"):
        op.drop_index("ix_webhooks_event_type_enabled", table_name="webhooks")
    if _has_table("webhooks"):
        op.drop_table("webhooks")

    if _has_index("pages", "ix_pages_published_slug"):
        op.drop_index("ix_pages_published_slug", table_name="pages")
    if _has_table("pages"):
        op.drop_table("pages")

    if _has_column("posts", "newsletter_attempts"):
        with op.batch_alter_table("posts", schema=None) as batch_op:
            batch_op.drop_column("newsletter_attempts")
    if _has_column("posts", "image_alt_text"):
        with op.batch_alter_table("posts", schema=None) as batch_op:
            batch_op.drop_column("image_alt_text")
