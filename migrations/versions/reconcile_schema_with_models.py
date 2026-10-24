"""Reconcile the schema with the models

Revision ID: reconcile_schema_with_models
Revises: add_page_menu_fields
Create Date: 2026-10-24

A database that was created with ``db.create_all()`` and then stamped has
always had the model's schema. A database that is built by running the
migration graph from empty does not: the graph predates several models, and
the columns and tables those models need were never added by a migration.

This revision closes that gap. Every step is conditional, so on a database
that already matches the models it changes nothing, and on a database built
by the migration graph it adds exactly what is missing.

The steps are:

* create ``api_tokens``, which no migration ever created
* add the ``users`` columns the model declares and the graph never added
* add the ``webhook_events`` delivery counters
* create the ``post_tags`` tag index the model declares
* drop ``users.totp_secret`` and ``webhooks.secret``, which the models
  replaced with ``totp_secret_encrypted`` and ``webhook_secret_encrypted``
* align the nullability of the columns the models declare as not nullable
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "reconcile_schema_with_models"
down_revision = "add_page_menu_fields"
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


def _is_nullable(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return True
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return bool(col["nullable"])
    return True


def _add_column(table: str, column: sa.Column) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.add_column(column)


def _drop_column(table: str, column: str) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.drop_column(column)


def _set_nullable(
    table: str, column: str, column_type: sa.types.TypeEngine, nullable: bool
) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=column_type, nullable=nullable)


def upgrade():
    if not _has_table("api_tokens"):
        op.create_table(
            "api_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("api_tokens", "ix_api_tokens_token_hash"):
        op.create_index("ix_api_tokens_token_hash", "api_tokens", ["token_hash"], unique=False)
    if not _has_index("api_tokens", "ix_api_tokens_revoked_at"):
        op.create_index("ix_api_tokens_revoked_at", "api_tokens", ["revoked_at"], unique=False)

    user_columns = [
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("reset_token", sa.String(length=64), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("totp_secret_encrypted", sa.String(length=256), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("backup_codes_hashed", sa.JSON(), nullable=True),
    ]
    for column in user_columns:
        if not _has_column("users", column.name):
            _add_column("users", column)

    for column in [
        sa.Column("successful_deliveries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_deliveries", sa.Integer(), nullable=False, server_default="0"),
    ]:
        if not _has_column("webhook_events", column.name):
            _add_column("webhook_events", column)

    if not _has_index("post_tags", "ix_post_tags_tag_id"):
        op.create_index("ix_post_tags_tag_id", "post_tags", ["tag_id"], unique=False)

    if _has_column("users", "totp_secret"):
        _drop_column("users", "totp_secret")

    if _has_column("webhooks", "secret"):
        _drop_column("webhooks", "secret")

    if _has_column("posts", "published"):
        op.execute("UPDATE posts SET published = 0 WHERE published IS NULL")
        if _is_nullable("posts", "published"):
            _set_nullable("posts", "published", sa.Boolean(), False)

    if _has_column("pages", "published"):
        op.execute("UPDATE pages SET published = 0 WHERE published IS NULL")
        if _is_nullable("pages", "published"):
            _set_nullable("pages", "published", sa.Boolean(), False)

    if _has_column("site_settings", "custom_css"):
        op.execute("UPDATE site_settings SET custom_css = '' WHERE custom_css IS NULL")
        if _is_nullable("site_settings", "custom_css"):
            _set_nullable("site_settings", "custom_css", sa.Text(), False)

    if _has_column("site_settings", "logo_text"):
        op.execute("UPDATE site_settings SET logo_text = '' WHERE logo_text IS NULL")
        if _is_nullable("site_settings", "logo_text"):
            _set_nullable("site_settings", "logo_text", sa.String(), False)

    for table in ("comments", "post_revisions", "webhooks"):
        if _has_column(table, "created_at") and not _is_nullable(table, "created_at"):
            _set_nullable(table, "created_at", sa.DateTime(), True)


def downgrade():
    _set_nullable("webhooks", "created_at", sa.DateTime(), False)
    _set_nullable("post_revisions", "created_at", sa.DateTime(), False)
    _set_nullable("comments", "created_at", sa.DateTime(), False)

    _set_nullable("site_settings", "logo_text", sa.String(), True)
    _set_nullable("site_settings", "custom_css", sa.Text(), True)
    _set_nullable("pages", "published", sa.Boolean(), True)
    _set_nullable("posts", "published", sa.Boolean(), True)

    if _has_column("webhooks", "secret"):
        _add_column("webhooks", sa.Column("secret", sa.String(length=64), nullable=True))

    if _has_column("users", "totp_secret"):
        _add_column("users", sa.Column("totp_secret", sa.String(length=32), nullable=True))

    if _has_index("post_tags", "ix_post_tags_tag_id"):
        op.drop_index("ix_post_tags_tag_id", table_name="post_tags")

    for column in [
        sa.Column("failed_deliveries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_deliveries", sa.Integer(), nullable=False, server_default="0"),
    ]:
        if _has_column("webhook_events", column.name):
            _drop_column("webhook_events", column.name)

    for column in [
        sa.Column("backup_codes_hashed", sa.JSON(), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("totp_secret_encrypted", sa.String(length=256), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reset_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("reset_token", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
    ]:
        if _has_column("users", column.name):
            _drop_column("users", column.name)

    if _has_table("api_tokens"):
        op.drop_table("api_tokens")
