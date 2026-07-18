"""End-to-end integration tests for the diagnostic framework.

Simulates healthy and broken installations, verifying doctor output.
"""

from __future__ import annotations

import json

from app.services.operations.doctor import (
    CheckStatus,
    get_registry,
    run_doctor,
)


class TestHealthyInstallation:
    """Tests simulating a healthy DevLog installation."""

    def test_healthy_run_all_required_pass(self, app, db):
        with app.app_context():
            result = run_doctor()
            required_checks = [c for c in result.checks if c.severity == "required"]
            for c in required_checks:
                assert c.status in ("pass", "skip", "warn"), (
                    f"Required check {c.check_id} failed: {c.summary}"
                )

    def test_healthy_run_no_errors(self, app, db):
        with app.app_context():
            result = run_doctor()
            error_checks = [c for c in result.checks if c.status == "error"]
            assert len(error_checks) == 0, f"Error checks: {[c.check_id for c in error_checks]}"

    def test_healthy_run_json_structure(self, app, db):
        with app.app_context():
            result = run_doctor()
            d = result.to_dict()
            serialized = json.dumps(d, default=str)
            parsed = json.loads(serialized)
            assert "ok" in parsed
            assert "status" in parsed
            assert "details" in parsed
            assert "checks" in parsed["details"]
            assert "paths" in parsed["details"]
            assert isinstance(parsed["details"]["checks"], list)
            assert len(parsed["details"]["checks"]) > 50

    def test_healthy_run_human_output_fields(self, app, db):
        with app.app_context():
            result = run_doctor()
            assert result.mode != ""
            assert result.version != ""
            assert result.duration_ms > 0
            assert result.code in ("doctor.ok", "doctor.degraded", "doctor.failed")

    def test_healthy_run_has_all_categories(self, app, db):
        with app.app_context():
            result = run_doctor()
            categories = {c.category for c in result.checks}
            expected = {
                "installation",
                "configuration",
                "secrets",
                "filesystem",
                "database",
                "search",
                "assets",
                "themes",
                "redis",
                "celery",
                "scheduler",
                "email",
                "storage",
                "deployment",
                "service",
                "backup",
                "security",
                "health",
                "capacity",
                "proxy",
            }
            assert expected.issubset(categories), f"Missing categories: {expected - categories}"


class TestBrokenSecretKey:
    """Tests simulating missing or broken SECRET_KEY."""

    def test_missing_secret_key_fails_required(self, app, db, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.FAIL
            assert result.ok is False

    def test_placeholder_secret_key_fails(self, app, db, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "changeme")
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.FAIL
            assert "placeholder" in result.checks[0].summary.lower()

    def test_short_secret_key_warns(self, app, db, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "short")
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.WARN

    def test_missing_admin_password_fails_required(self, app, db, monkeypatch):
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.admin_password"])
            assert result.checks[0].status == CheckStatus.FAIL


class TestBrokenConfiguration:
    """Tests simulating broken configuration."""

    def test_config_load_failure(self, app, db, monkeypatch):
        def broken_load():
            raise RuntimeError("Config parse error")

        monkeypatch.setattr("app.config.loader.load_effective_config", broken_load)
        with app.app_context():
            result = run_doctor(check_ids=["config.load"])
            assert result.checks[0].status in ("fail", "error")

    def test_missing_database_connectivity(self, app, db, monkeypatch):
        def broken_execute(query):
            raise RuntimeError("Connection refused")

        monkeypatch.setattr(db.session, "execute", broken_execute)
        with app.app_context():
            result = run_doctor(check_ids=["db.connectivity"])
            assert result.checks[0].status == CheckStatus.FAIL


class TestBrokenFilesystem:
    """Tests simulating filesystem issues."""

    def test_missing_required_directories(self, app, db, monkeypatch, tmp_path):
        import app.services.operations.doctor as doc

        fake_paths = type(
            "FakePaths",
            (),
            {
                "data_dir": type("P", (), {"path": tmp_path / "nonexistent_data"})(),
                "uploads_dir": type("P", (), {"path": tmp_path / "nonexistent_uploads"})(),
                "themes_dir": type("P", (), {"path": tmp_path / "nonexistent_themes"})(),
                "backups_dir": type("P", (), {"path": tmp_path / "nonexistent_backups"})(),
                "exports_dir": type("P", (), {"path": tmp_path / "nonexistent_exports"})(),
                "log_dir": type("P", (), {"path": tmp_path / "nonexistent_log"})(),
                "runtime_dir": type("P", (), {"path": tmp_path / "nonexistent_runtime"})(),
            },
        )()
        original_fn = doc._ctx_paths
        doc._ctx_paths = lambda: fake_paths
        try:
            with app.app_context():
                result = run_doctor(check_ids=["fs.required_dirs"])
                assert result.checks[0].status == CheckStatus.WARN
                assert "missing" in result.checks[0].summary.lower()
        finally:
            doc._ctx_paths = original_fn

    def test_low_disk_space(self, app, db, monkeypatch):
        import shutil

        class FakeUsage:
            total = 1000 * 1024 * 1024
            free = 10 * 1024 * 1024
            used = 990 * 1024 * 1024

        monkeypatch.setattr(shutil, "disk_usage", lambda p: FakeUsage())
        with app.app_context():
            result = run_doctor(check_ids=["fs.disk_space"])
            assert result.checks[0].status == CheckStatus.FAIL
            assert "critically low" in result.checks[0].summary.lower()


class TestProductionMode:
    """Tests simulating production mode behavior."""

    def test_production_required_failures_cause_nonzero(self, app, db, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"], production=True)
            assert result.ok is False
            assert result.status == "failure"

    def test_production_mode_all_required_checks(self, app, db):
        with app.app_context():
            result = run_doctor(production=True)
            required_fails = [
                c
                for c in result.checks
                if c.severity == "required" and c.status in ("fail", "error")
            ]
            if required_fails:
                assert result.ok is False
                assert result.status == "failure"


class TestDryRunSafeFixes:
    """Tests for dry-run safe fix mode."""

    def test_dry_run_does_not_apply_fixes(self, app, db):
        with app.app_context():
            result = run_doctor(
                check_ids=["install.secret_permissions"], fix_safe=True, dry_run=True
            )
            assert isinstance(result.safe_fix_plan, list)

    def test_dry_run_plan_structure(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.required_dirs"], fix_safe=True, dry_run=True)
            if result.safe_fix_plan:
                fix = result.safe_fix_plan[0]
                assert "fix_id" in fix
                assert "description" in fix
                assert "check_id" in fix


class TestParallelVsSequential:
    """Tests comparing parallel and sequential execution."""

    def test_same_check_ids_parallel_vs_sequential(self, app, db):
        with app.app_context():
            check_list = ["pkg.version", "config.load", "db.connectivity", "secrets.secret_key"]
            r_par = run_doctor(check_ids=check_list, parallel=True)
            r_seq = run_doctor(check_ids=check_list, parallel=False)
            par_ids = {c.check_id for c in r_par.checks}
            seq_ids = {c.check_id for c in r_seq.checks}
            assert par_ids == seq_ids

    def test_parallel_full_run(self, app, db):
        with app.app_context():
            result = run_doctor(parallel=True)
            assert len(result.checks) > 50
            assert result.duration_ms > 0


class TestCheckRegistryCompleteness:
    """Tests verifying the check registry is complete."""

    def test_all_expected_check_ids_exist(self):
        registry = get_registry()
        expected_ids = [
            "pkg.version",
            "config.load",
            "config.validate",
            "secrets.secret_key",
            "secrets.admin_password",
            "install.metadata",
            "install.release_symlink",
            "install.config_path",
            "install.deprecated_keys",
            "install.secret_permissions",
            "install.stale_metadata",
            "fs.required_dirs",
            "fs.disk_space",
            "fs.symlink_safety",
            "fs.ownership",
            "fs.writable",
            "fs.inodes",
            "fs.type",
            "fs.docker_uid",
            "fs.stale_files",
            "fs.legacy_remnants",
            "db.connectivity",
            "db.migration_head",
            "db.sqlite_integrity",
            "db.fts5",
            "db.path_match",
            "db.wal_checkpoint",
            "db.ownership",
            "db.fts_health",
            "db.orphaned_migration",
            "db.backend_features",
            "assets.frontend_manifest",
            "assets.referenced",
            "assets.upload_serving",
            "themes.bundled",
            "themes.selected",
            "themes.accessibility",
            "themes.attribution",
            "themes.external_dir",
            "dep.redis",
            "dep.redis_auth",
            "dep.redis_db",
            "dep.celery",
            "dep.celery_workers",
            "dep.celery_routing",
            "dep.celery_version",
            "dep.scheduler",
            "dep.scheduler_stale",
            "dep.scheduler_runs",
            "dep.scheduler_owner",
            "dep.smtp",
            "dep.smtp_connect",
            "dep.storage",
            "dep.storage_writable",
            "dep.storage_s3_probe",
            "deploy.mode",
            "deploy.drift",
            "deploy.service_state",
            "deploy.files",
            "deploy.health_endpoint",
            "deploy.proxy",
            "deploy.bind",
            "deploy.pid",
            "deploy.restart_loop",
            "deploy.systemd_syntax",
            "deploy.process_version",
            "deploy.image_match",
            "backup.readiness",
            "backup.manifest",
            "backup.encryption",
            "backup.retention",
            "backup.verification",
            "backup.path_nesting",
            "security.session",
            "security.secrets",
            "security.cookie",
        ]
        all_ids = set(registry.all_ids())
        missing = set(expected_ids) - all_ids
        assert not missing, f"Missing check IDs: {missing}"

    def test_total_check_count(self):
        registry = get_registry()
        assert len(registry.all_ids()) >= 76
