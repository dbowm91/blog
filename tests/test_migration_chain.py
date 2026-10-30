"""Real Alembic revision-chain tests for Halloy theme migrations.

Tests the specific Halloy theme migrations by invoking their upgrade/downgrade
functions within a proper Alembic Operations context.

The last test builds a database from scratch with the whole migration graph
and compares the result with the models. The graph has two branches that
leave ``1992db4c5c98`` and both branches create some of the same objects, so
a fresh install is the case that exercises the branch interaction.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _expected_head() -> str:
    """The single head of the migration graph, read from the revision scripts.

    Deriving it keeps the fresh-install test meaningful after every new
    revision instead of pinning a revision name that goes stale.
    """
    revisions: set[str] = set()
    parents: set[str] = set()
    for path in (REPO_ROOT / "migrations" / "versions").glob("*.py"):
        text = path.read_text()
        revision = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', text, re.M)
        if not revision:
            continue
        revisions.add(revision.group(1))
        down = re.search(r"^down_revision\s*=\s*(.+)$", text, re.M)
        if down:
            parents.update(re.findall(r'["\']([^"\']+)["\']', down.group(1)))

    heads = sorted(revisions - parents)
    assert len(heads) == 1, f"expected a single migration head, found {heads}"
    return heads[0]


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


def test_drop_syntax_theme_removes_the_column(app):
    """drop_syntax_theme_column removes the retired syntax_theme column."""
    with app.app_context():
        from app.extensions import db

        engine = db.engine
        _create_pre_halloy_schema(engine)

        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO site_settings DEFAULT VALUES"))

        from migrations.versions.drop_syntax_theme_column import (
            downgrade as downgrade_drop,
            upgrade as upgrade_drop,
        )

        columns = _get_columns(engine, "site_settings")
        assert "syntax_theme" in columns

        _run_migration(engine, upgrade_drop)

        columns = _get_columns(engine, "site_settings")
        assert "syntax_theme" not in columns
        assert "custom_css_enabled" in columns

        _run_migration(engine, downgrade_drop)

        restored = _get_columns(engine, "site_settings")
        assert "syntax_theme" in restored

        rows = _get_all_rows(engine, "site_settings")
        assert rows[0]["syntax_theme"] == "prism"

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE site_settings"))


def test_project_features_migration_is_the_head(app):
    """The project feature revision is the single head of the graph."""
    assert _expected_head() == "add_project_features"


def test_project_migrations_upgrade_and_downgrade(tmp_path):
    """The project schema and navigation settings migrate reversibly."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'project-migrations.sqlite3'}")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE site_settings (id INTEGER PRIMARY KEY)"))

    from migrations.versions.add_project_navigation_settings import (
        downgrade as downgrade_navigation,
        upgrade as upgrade_navigation,
    )
    from migrations.versions.add_project_documents import (
        downgrade as downgrade_documents,
        upgrade as upgrade_documents,
    )
    from migrations.versions.add_project_features import (
        downgrade as downgrade_features,
        upgrade as upgrade_features,
    )
    from migrations.versions.add_project_github_docs_snapshots import (
        downgrade as downgrade_docs_snapshots,
        upgrade as upgrade_docs_snapshots,
    )
    from migrations.versions.add_project_releases import (
        downgrade as downgrade_releases,
        upgrade as upgrade_releases,
    )
    from migrations.versions.add_project_sync_leases import (
        downgrade as downgrade_sync_leases,
        upgrade as upgrade_sync_leases,
    )
    from migrations.versions.add_projects_table import (
        downgrade as downgrade_projects,
        upgrade as upgrade_projects,
    )

    _run_migrations(
        engine,
        upgrade_projects,
        upgrade_navigation,
        upgrade_documents,
        upgrade_docs_snapshots,
        upgrade_releases,
        upgrade_sync_leases,
        upgrade_features,
    )

    inspector = sa.inspect(engine)
    assert inspector.has_table("projects")
    assert inspector.has_table("project_documents")
    assert inspector.has_table("project_document_assets")
    assert inspector.has_table("project_docs_snapshots")
    assert inspector.has_table("project_releases")
    assert inspector.has_table("project_release_assets")
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    assert {"docs_enabled", "active_docs_snapshot_id", "releases_enabled"} <= project_columns
    assert {
        "docs_sync_lease_owner",
        "docs_sync_lease_expires_at",
        "releases_sync_lease_owner",
        "releases_sync_lease_expires_at",
        "releases_sync_config",
    } <= project_columns
    assert "features" in project_columns
    settings_columns = {column["name"] for column in inspector.get_columns("site_settings")}
    assert {
        "show_projects_in_menu",
        "projects_menu_label",
        "homepage_kind",
        "homepage_target_id",
    } <= settings_columns
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO site_settings (id) VALUES (1)"))
    row = _get_all_rows(engine, "site_settings")[0]
    assert row["show_projects_in_menu"] == 0
    assert row["projects_menu_label"] == "Projects"
    assert row["homepage_kind"] == "blog"
    assert row["homepage_target_id"] is None

    _run_migration(engine, downgrade_features)
    _run_migration(engine, downgrade_sync_leases)
    _run_migration(engine, downgrade_releases)
    _run_migration(engine, downgrade_docs_snapshots)
    _run_migration(engine, downgrade_documents)
    _run_migration(engine, downgrade_navigation)
    _run_migration(engine, downgrade_projects)
    final_inspector = sa.inspect(engine)
    assert not final_inspector.has_table("projects")
    assert not final_inspector.has_table("project_documents")
    assert not final_inspector.has_table("project_docs_snapshots")
    assert not final_inspector.has_table("project_releases")
    assert {column["name"] for column in sa.inspect(engine).get_columns("site_settings")} == {"id"}
    engine.dispose()


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


def _fresh_install(tmp_path):
    """Build a database from scratch with the whole migration graph.

    The upgrade runs in a subprocess because the migration environment reads
    the engine from the current Flask application, and the test suite's own
    application is bound to a different database.
    """
    db_path = tmp_path / "fresh.sqlite3"
    env = os.environ.copy()
    env["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    env["FLASK_APP"] = "run:app"
    env.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
    env.setdefault("ADMIN_PASSWORD", "test-password-123")

    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return db_path


def test_fresh_install_upgrades_without_error(tmp_path):
    """A database built from scratch runs every migration.

    The graph has two branches that leave 1992db4c5c98. Both of them create
    some of the same objects - 89a922eae517 adds posts.newsletter_attempts and
    add_post_revisions creates the post_revisions table - and 16034e1c5a45
    creates them too. A fresh install runs both branches, so the DDL has to
    tolerate arriving second.
    """
    db_path = _fresh_install(tmp_path)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    assert version == _expected_head()


def test_fresh_install_adds_the_appearance_columns(tmp_path):
    """The appearance settings are part of the schema a fresh install produces."""
    db_path = _fresh_install(tmp_path)

    engine = sa.create_engine(f"sqlite:///{db_path}")

    columns = _get_columns(engine, "site_settings")
    assert {"font_sans", "font_mono", "backdrop"} <= columns


def test_fresh_install_schema_matches_the_models(tmp_path):
    """The schema a fresh install produces is the schema the models describe."""
    from app.extensions import db

    db_path = _fresh_install(tmp_path)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)

    problems = []
    for name, table in db.metadata.tables.items():
        if not inspector.has_table(name):
            problems.append(f"missing table {name}")
            continue
        actual = {col["name"] for col in inspector.get_columns(name)}
        expected = {col.name for col in table.columns}
        missing = expected - actual
        if missing:
            problems.append(f"{name}: missing columns {sorted(missing)}")

    assert not problems, "\n".join(problems)
