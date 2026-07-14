"""Real Alembic revision-chain tests for Halloy theme migrations.

Tests the specific Halloy theme migrations by invoking their upgrade/downgrade
functions within a proper Alembic Operations context.
"""

import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations


def _get_columns(engine, table_name):
    """Return set of column names for a table."""
    insp = sa.inspect(engine)
    return {col["name"] for col in insp.get_columns(table_name)}


def _create_pre_halloy_schema(engine):
    """Create the site_settings table at the state just before Halloy migrations."""
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS site_settings"))
        conn.execute(
            sa.text(
                "CREATE TABLE site_settings ("
                " id INTEGER PRIMARY KEY,"
                " theme_preset TEXT NOT NULL DEFAULT 'github-dark',"
                " custom_css_enabled BOOLEAN NOT NULL DEFAULT 0,"
                " custom_css TEXT DEFAULT '',"
                " logo_text TEXT DEFAULT '',"
                " updated_at DATETIME DEFAULT NULL,"
                " syntax_theme TEXT NOT NULL DEFAULT 'prism'"
                ")"
            )
        )


def _get_all_rows(engine, table_name):
    """Return all rows from a table as list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(sa.text(f"SELECT * FROM {table_name}"))
        return [dict(row._mapping) for row in result]


def _run_migration(engine, upgrade_fn):
    """Run a migration function and commit the connection."""
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            upgrade_fn()
        conn.commit()


def _run_migrations(engine, *upgrade_fns):
    """Run multiple migration functions in sequence and commit."""
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            for fn in upgrade_fns:
                fn()
        conn.commit()


def _run_upgrade_downgrade(engine, upgrade_fn, downgrade_fn):
    """Run upgrade then downgrade and commit."""
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            upgrade_fn()
        conn.commit()
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            downgrade_fn()
        conn.commit()


def test_add_theme_config_adds_columns(app):
    """add_theme_config_to_sitesettings adds dark/light/scheme columns."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        from migrations.versions.add_theme_config_to_sitesettings import upgrade

        _run_migration(engine, upgrade)

        columns = _get_columns(engine, "site_settings")
        assert "theme_dark_name" in columns
        assert "theme_light_name" in columns
        assert "theme_default_scheme" in columns
        assert "theme_preset" in columns

        rows = _get_all_rows(engine, "site_settings")
        assert len(rows) == 0

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_preset_mapping_applied(app):
    """Legacy preset values map to correct Halloy theme names."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        with engine.begin() as conn:
            for preset in [
                "github-dark",
                "github-light",
                "solarized-dark",
                "monokai",
                "custom-theme",
                "",
            ]:
                conn.execute(
                    sa.text("INSERT INTO site_settings (theme_preset) VALUES (:p)"),
                    {"p": preset},
                )

        from migrations.versions.add_theme_config_to_sitesettings import upgrade

        _run_migration(engine, upgrade)

        rows = _get_all_rows(engine, "site_settings")
        assert len(rows) == 6

        github_dark = next(r for r in rows if r["theme_preset"] == "github-dark")
        assert github_dark["theme_dark_name"] == "Catppuccin Mocha"
        assert github_dark["theme_default_scheme"] == "system"

        github_light = next(r for r in rows if r["theme_preset"] == "github-light")
        assert github_light["theme_light_name"] == "Catppuccin Latte"

        solarized = next(r for r in rows if r["theme_preset"] == "solarized-dark")
        assert solarized["theme_dark_name"] == "Solarized Dark"

        monokai = next(r for r in rows if r["theme_preset"] == "monokai")
        assert monokai["theme_dark_name"] == "Sonokai"

        unknown = next(r for r in rows if r["theme_preset"] == "custom-theme")
        assert unknown["theme_dark_name"] == "Catppuccin Mocha"
        assert unknown["theme_default_scheme"] == "system"

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_preserve_legacy_scheme(app):
    """preserve_legacy_scheme fixes theme_default_scheme for dark/light presets."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        with engine.begin() as conn:
            for preset in ["github-dark", "github-light", "solarized-dark"]:
                conn.execute(
                    sa.text("INSERT INTO site_settings (theme_preset) VALUES (:p)"),
                    {"p": preset},
                )

        from migrations.versions.add_theme_config_to_sitesettings import upgrade as upgrade_add
        from migrations.versions.preserve_legacy_scheme import upgrade as upgrade_preserve

        _run_migrations(engine, upgrade_add, upgrade_preserve)

        rows = _get_all_rows(engine, "site_settings")

        github_dark = next(r for r in rows if r["theme_preset"] == "github-dark")
        assert github_dark["theme_default_scheme"] == "dark"

        github_light = next(r for r in rows if r["theme_preset"] == "github-light")
        assert github_light["theme_default_scheme"] == "light"

        solarized = next(r for r in rows if r["theme_preset"] == "solarized-dark")
        assert solarized["theme_default_scheme"] == "dark"

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_drop_theme_preset_removes_column(app):
    """drop_theme_preset_column removes the theme_preset column."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO site_settings (theme_preset) VALUES ('github-dark')"))

        from migrations.versions.add_theme_config_to_sitesettings import upgrade as upgrade_add
        from migrations.versions.preserve_legacy_scheme import upgrade as upgrade_preserve
        from migrations.versions.drop_theme_preset_column import upgrade as upgrade_drop

        _run_migrations(engine, upgrade_add, upgrade_preserve, upgrade_drop)

        columns = _get_columns(engine, "site_settings")
        assert "theme_preset" not in columns
        assert "theme_dark_name" in columns
        assert "theme_light_name" in columns
        assert "theme_default_scheme" in columns

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_full_chain_round_trip(app):
    """Full chain: add -> preserve -> drop -> downgrade -> re-upgrade."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO site_settings (theme_preset) VALUES ('github-dark')"))

        from migrations.versions.add_theme_config_to_sitesettings import upgrade as upgrade_add
        from migrations.versions.preserve_legacy_scheme import upgrade as upgrade_preserve
        from migrations.versions.drop_theme_preset_column import (
            upgrade as upgrade_drop,
            downgrade as downgrade_drop,
        )

        _run_migrations(engine, upgrade_add, upgrade_preserve, upgrade_drop)

        columns = _get_columns(engine, "site_settings")
        assert "theme_preset" not in columns

        _run_migration(engine, downgrade_drop)

        columns_restored = _get_columns(engine, "site_settings")
        assert "theme_preset" in columns_restored

        _run_migration(engine, upgrade_drop)

        columns_final = _get_columns(engine, "site_settings")
        assert "theme_preset" not in columns_final
        assert "theme_dark_name" in columns_final

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_fresh_install_creates_correct_schema(app):
    """Fresh database gets correct defaults without any legacy data."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS site_settings"))
            conn.execute(
                sa.text(
                    "CREATE TABLE site_settings ("
                    " id INTEGER PRIMARY KEY,"
                    " theme_preset TEXT NOT NULL DEFAULT 'github-dark',"
                    " custom_css_enabled BOOLEAN NOT NULL DEFAULT 0,"
                    " custom_css TEXT DEFAULT '',"
                    " logo_text TEXT DEFAULT '',"
                    " updated_at DATETIME DEFAULT NULL,"
                    " syntax_theme TEXT NOT NULL DEFAULT 'prism'"
                    ")"
                )
            )

        from migrations.versions.add_theme_config_to_sitesettings import upgrade as upgrade_add
        from migrations.versions.preserve_legacy_scheme import upgrade as upgrade_preserve
        from migrations.versions.drop_theme_preset_column import upgrade as upgrade_drop

        _run_migrations(engine, upgrade_add, upgrade_preserve, upgrade_drop)

        columns = _get_columns(engine, "site_settings")
        assert "theme_dark_name" in columns
        assert "theme_light_name" in columns
        assert "theme_default_scheme" in columns
        assert "theme_preset" not in columns

        rows = _get_all_rows(engine, "site_settings")
        assert len(rows) == 0

        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO site_settings DEFAULT VALUES"))

        rows = _get_all_rows(engine, "site_settings")
        assert len(rows) == 1
        row = rows[0]
        assert row["theme_dark_name"] == "Catppuccin Mocha"
        assert row["theme_light_name"] == "Catppuccin Latte"
        assert row["theme_default_scheme"] == "system"
        assert row["syntax_theme"] == "prism"
        assert row["custom_css_enabled"] == 0
        assert row["custom_css"] == ""

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))
