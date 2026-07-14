"""Round-trip test for drop_theme_preset_column migration.

Verifies upgrade() drops the column and downgrade() restores it.
"""

import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations


def _get_columns(engine, table_name):
    """Return set of column names for a table."""
    insp = sa.inspect(engine)
    return {col["name"] for col in insp.get_columns(table_name)}


def _create_table_with_preset(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS site_settings"))
        conn.execute(
            sa.text(
                "CREATE TABLE site_settings ("
                " id INTEGER PRIMARY KEY,"
                " site_title TEXT NOT NULL DEFAULT 'Blog',"
                " theme_preset TEXT NOT NULL DEFAULT 'github-dark'"
                ")"
            )
        )


def _create_table_without_preset(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS site_settings"))
        conn.execute(
            sa.text(
                "CREATE TABLE site_settings ("
                " id INTEGER PRIMARY KEY,"
                " site_title TEXT NOT NULL DEFAULT 'Blog'"
                ")"
            )
        )


def test_upgrade_drops_theme_preset(app):
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_table_with_preset(engine)
        assert "theme_preset" in _get_columns(engine, "site_settings")

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx) as op:
                with op.batch_alter_table("site_settings") as batch_op:
                    batch_op.drop_column("theme_preset")

        columns = _get_columns(engine, "site_settings")
        assert "theme_preset" not in columns
        assert "site_title" in columns

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_downgrade_restores_theme_preset(app):
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_table_without_preset(engine)
        assert "theme_preset" not in _get_columns(engine, "site_settings")

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx) as op:
                with op.batch_alter_table("site_settings") as batch_op:
                    batch_op.add_column(
                        sa.Column(
                            "theme_preset",
                            sa.String(length=32),
                            nullable=False,
                            server_default="github-dark",
                        )
                    )

        columns = _get_columns(engine, "site_settings")
        assert "theme_preset" in columns
        assert "site_title" in columns

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_round_trip_preserves_data(app):
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_table_with_preset(engine)

        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO site_settings (site_title, theme_preset)"
                    " VALUES ('My Blog', 'solarized-dark')"
                )
            )

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx) as op:
                with op.batch_alter_table("site_settings") as batch_op:
                    batch_op.drop_column("theme_preset")

        assert "theme_preset" not in _get_columns(engine, "site_settings")

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx) as op:
                with op.batch_alter_table("site_settings") as batch_op:
                    batch_op.add_column(
                        sa.Column(
                            "theme_preset",
                            sa.String(length=32),
                            nullable=False,
                            server_default="github-dark",
                        )
                    )

        assert "theme_preset" in _get_columns(engine, "site_settings")

        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT site_title FROM site_settings")).fetchone()
            assert row[0] == "My Blog"

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))
