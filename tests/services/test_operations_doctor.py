"""Tests for app.services.operations.doctor — diagnostic framework."""

from __future__ import annotations



from app.services.operations.doctor import (
    CheckCategory,
    CheckDefinition,
    CheckRegistry,
    CheckResult,
    CheckStatus,
    DoctorResult,
    Severity,
    get_registry,
    get_safe_fix_plan,
    redact_details,
    register_safe_fix,
    run_doctor,
)


# ---------------------------------------------------------------------------
# CheckRegistry tests
# ---------------------------------------------------------------------------


class TestCheckRegistry:
    def test_register_and_get(self):
        reg = CheckRegistry()
        defn = CheckDefinition("test.1", "filesystem", "Test check")

        def _runner(**kw: object) -> CheckResult:
            return CheckResult("test.1", "filesystem", "pass", "recommended", "ok")

        reg.register(defn, _runner)
        result = reg.get("test.1")
        assert result is not None
        assert result[0].check_id == "test.1"
        assert result[1] is _runner

    def test_get_nonexistent(self):
        reg = CheckRegistry()
        assert reg.get("nope") is None

    def test_list_checks_all(self):
        reg = CheckRegistry()
        reg.register(
            CheckDefinition("a.1", "filesystem", "A"),
            lambda **kw: CheckResult("a.1", "filesystem", "pass", "recommended", "ok"),
        )
        reg.register(
            CheckDefinition("b.1", "database", "B"),
            lambda **kw: CheckResult("b.1", "database", "pass", "required", "ok"),
        )
        checks = reg.list_checks()
        assert len(checks) == 2
        ids = [c.check_id for c in checks]
        assert "a.1" in ids
        assert "b.1" in ids

    def test_list_checks_by_category(self):
        reg = CheckRegistry()
        reg.register(
            CheckDefinition("a.1", "filesystem", "A"),
            lambda **kw: CheckResult("a.1", "filesystem", "pass", "recommended", "ok"),
        )
        reg.register(
            CheckDefinition("b.1", "database", "B"),
            lambda **kw: CheckResult("b.1", "database", "pass", "required", "ok"),
        )
        checks = reg.list_checks(category="filesystem")
        assert len(checks) == 1
        assert checks[0].check_id == "a.1"

    def test_list_checks_production_only(self):
        reg = CheckRegistry()
        reg.register(
            CheckDefinition("a.1", "filesystem", "A", production_required=False),
            lambda **kw: CheckResult("a.1", "filesystem", "pass", "optional", "ok"),
        )
        reg.register(
            CheckDefinition("b.1", "database", "B", production_required=True),
            lambda **kw: CheckResult("b.1", "database", "pass", "required", "ok"),
        )
        checks = reg.list_checks(production_only=True)
        assert len(checks) == 1
        assert checks[0].check_id == "b.1"

    def test_all_ids(self):
        reg = CheckRegistry()
        reg.register(
            CheckDefinition("z.1", "filesystem", "Z"),
            lambda **kw: None,
        )
        reg.register(
            CheckDefinition("a.1", "filesystem", "A"),
            lambda **kw: None,
        )
        ids = reg.all_ids()
        assert ids == ["a.1", "z.1"]


# ---------------------------------------------------------------------------
# CheckStatus / CheckCategory / Severity enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_check_status_values(self):
        assert CheckStatus.PASS == "pass"
        assert CheckStatus.WARN == "warn"
        assert CheckStatus.FAIL == "fail"
        assert CheckStatus.SKIP == "skip"
        assert CheckStatus.ERROR == "error"

    def test_check_category_values(self):
        assert CheckCategory.DATABASE == "database"
        assert CheckCategory.FILESYSTEM == "filesystem"
        assert CheckCategory.THEMES == "themes"

    def test_severity_values(self):
        assert Severity.REQUIRED == "required"
        assert Severity.RECOMMENDED == "recommended"
        assert Severity.OPTIONAL == "optional"


# ---------------------------------------------------------------------------
# CheckResult and DoctorResult tests
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_creation(self):
        cr = CheckResult(
            check_id="test.1",
            category="filesystem",
            status="pass",
            severity="recommended",
            summary="All good",
        )
        assert cr.check_id == "test.1"
        assert cr.status == "pass"
        assert cr.duration_ms == 0.0
        assert cr.details == {}
        assert cr.remediation == []
        assert cr.safe_fix_id is None

    def test_with_details(self):
        cr = CheckResult(
            check_id="test.1",
            category="filesystem",
            status="pass",
            severity="recommended",
            summary="ok",
            details={"free_mb": 1024.0},
        )
        assert cr.details["free_mb"] == 1024.0


class TestDoctorResult:
    def test_to_dict(self):
        cr = CheckResult("a.1", "filesystem", "pass", "recommended", "ok")
        dr = DoctorResult(
            ok=True,
            status="healthy",
            code="doctor.ok",
            summary="All checks passed",
            mode="development",
            version="1.0.0",
            checks=[cr],
        )
        d = dr.to_dict()
        assert d["ok"] is True
        assert d["status"] == "healthy"
        assert d["code"] == "doctor.ok"
        assert len(d["details"]["checks"]) == 1
        assert d["details"]["checks"][0]["check_id"] == "a.1"

    def test_to_dict_empty(self):
        dr = DoctorResult(ok=True, status="healthy", code="doctor.ok", summary="ok")
        d = dr.to_dict()
        assert d["details"]["checks"] == []


# ---------------------------------------------------------------------------
# Redaction tests
# ---------------------------------------------------------------------------


class TestRedactDetails:
    def test_redacts_secret_keys(self):
        details = {"secret_key": "abcdef1234567890", "host": "localhost"}
        redacted = redact_details(details)
        assert redacted["host"] == "localhost"
        assert "ab" in redacted["secret_key"]
        assert "****" in redacted["secret_key"]
        assert redacted["secret_key"] != "abcdef1234567890"

    def test_redacts_password(self):
        details = {"admin_password": "mypassword123"}
        redacted = redact_details(details)
        assert redacted["admin_password"] != "mypassword123"
        assert "****" in redacted["admin_password"]

    def test_redacts_nested_dicts(self):
        details = {"config": {"secret_key": "abcdef123456"}}
        redacted = redact_details(details)
        assert redacted["config"]["secret_key"] != "abcdef123456"

    def test_empty_values(self):
        details = {"secret_key": ""}
        redacted = redact_details(details)
        assert redacted["secret_key"] == "****"

    def test_short_values(self):
        details = {"token": "abc"}
        redacted = redact_details(details)
        assert redacted["token"] == "****"


# ---------------------------------------------------------------------------
# run_doctor tests
# ---------------------------------------------------------------------------


class TestRunDoctor:
    def test_run_doctor_returns_doctor_result(self, app, db):
        with app.app_context():
            result = run_doctor()
            assert isinstance(result, DoctorResult)
            assert result.mode in ("development", "system", "user", "docker", "unknown")
            assert len(result.checks) > 0

    def test_run_doctor_all_pass(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
            assert len(result.checks) == 1
            assert result.checks[0].status == CheckStatus.PASS

    def test_run_doctor_category_filter(self, app, db):
        with app.app_context():
            result = run_doctor(category="nonexistent")
            assert len(result.checks) == 0
            assert result.ok is True

    def test_run_doctor_check_id_filter(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.connectivity"])
            assert len(result.checks) == 1
            assert result.checks[0].check_id == "db.connectivity"
            assert result.checks[0].status == CheckStatus.PASS

    def test_run_doctor_nonexistent_check(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["nonexistent.check"])
            assert len(result.checks) == 0

    def test_run_doctor_has_timing(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
            assert result.duration_ms > 0
            assert result.checks[0].duration_ms >= 0

    def test_run_doctor_has_mode_and_version(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
            assert result.mode != ""
            assert result.version != ""


# ---------------------------------------------------------------------------
# Safe fix tests
# ---------------------------------------------------------------------------


class TestSafeFixes:
    def test_get_safe_fix_plan_empty(self):
        cr = CheckResult("a.1", "filesystem", "pass", "recommended", "ok", safe_fix_id=None)
        plan = get_safe_fix_plan([cr])
        assert plan == []

    def test_get_safe_fix_plan_with_applicable(self):
        register_safe_fix("fix.test", "Test fix", "a.1")
        cr = CheckResult("a.1", "filesystem", "fail", "recommended", "bad", safe_fix_id="fix.test")
        plan = get_safe_fix_plan([cr])
        assert len(plan) == 1
        assert plan[0].fix_id == "fix.test"

    def test_get_safe_fix_plan_skips_passing(self):
        register_safe_fix("fix.pass", "Pass fix", "a.1")
        cr = CheckResult("a.1", "filesystem", "pass", "recommended", "ok", safe_fix_id="fix.pass")
        plan = get_safe_fix_plan([cr])
        assert plan == []


# ---------------------------------------------------------------------------
# Global registry tests
# ---------------------------------------------------------------------------


class TestGlobalRegistry:
    def test_get_registry_returns_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_global_registry_has_checks(self):
        reg = get_registry()
        ids = reg.all_ids()
        assert len(ids) > 10
        assert "db.connectivity" in ids
        assert "config.load" in ids
        assert "fs.required_dirs" in ids
        assert "themes.bundled" in ids

    def test_global_registry_categories(self):
        reg = get_registry()
        all_checks = reg.list_checks()
        categories = {c.category for c in all_checks}
        assert "database" in categories
        assert "filesystem" in categories
        assert "configuration" in categories
        assert "themes" in categories
        assert "installation" in categories
        assert "capacity" in categories


# ---------------------------------------------------------------------------
# Individual check integration tests
# ---------------------------------------------------------------------------


class TestDatabaseChecks:
    def test_db_connectivity_pass(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.connectivity"])
            assert result.checks[0].status == CheckStatus.PASS
            assert "connected" in result.checks[0].summary.lower()

    def test_db_migration_head(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.migration_head"])
            assert result.checks[0].status == CheckStatus.PASS
            assert "head" in result.checks[0].summary.lower()

    def test_db_integrity(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.sqlite_integrity"])
            assert result.checks[0].status == CheckStatus.PASS

    def test_fts5_check(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.fts5"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


class TestConfigurationChecks:
    def test_config_load(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["config.load"])
            assert result.checks[0].status == CheckStatus.PASS

    def test_config_validate(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["config.validate"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_secret_key_check(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.PASS

    def test_admin_password_check(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["secrets.admin_password"])
            assert result.checks[0].status == CheckStatus.PASS


class TestFilesystemChecks:
    def test_disk_space(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.disk_space"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_required_dirs(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.required_dirs"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


class TestThemeChecks:
    def test_bundled_themes(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["themes.bundled"])
            assert result.checks[0].status == CheckStatus.PASS
            assert result.checks[0].details.get("theme_count", 0) > 0

    def test_selected_themes(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["themes.selected"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.ERROR)


class TestDeploymentChecks:
    def test_deploy_mode(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.mode"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.ERROR)


class TestBackupChecks:
    def test_backup_readiness(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


class TestSecurityChecks:
    def test_session_security(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["security.session"])
            assert result.checks[0].status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# New check tests — H3 Installation
# ---------------------------------------------------------------------------


class TestInstallationChecks:
    def test_release_symlink(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_config_path(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["install.config_path"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_deprecated_keys(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_secret_permissions(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["install.secret_permissions"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_stale_metadata(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["install.stale_metadata"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)


# ---------------------------------------------------------------------------
# New check tests — H4 Filesystem
# ---------------------------------------------------------------------------


class TestFilesystemChecksNew:
    def test_dir_ownership(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_dir_writable(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.writable"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL)

    def test_inodes(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.inodes"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_fs_type(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_docker_uid(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_stale_files(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.stale_files"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_legacy_remnants(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["fs.legacy_remnants"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)


# ---------------------------------------------------------------------------
# New check tests — H5 Database
# ---------------------------------------------------------------------------


class TestDatabaseChecksNew:
    def test_wal_checkpoint(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.wal_checkpoint"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_db_ownership(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.ownership"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_fts_health(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.fts_health"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_migration_orphaned(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.orphaned_migration"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_backend_features(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.backend_features"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


# ---------------------------------------------------------------------------
# New check tests — H6 Assets
# ---------------------------------------------------------------------------


class TestAssetChecksNew:
    def test_referenced_assets(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["assets.referenced"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_theme_accessibility(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["themes.accessibility"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_theme_attribution(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["themes.attribution"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


# ---------------------------------------------------------------------------
# New check tests — H7 Dependencies
# ---------------------------------------------------------------------------


class TestDependencyChecksNew:
    def test_redis_auth(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_celery_workers(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_scheduler_stale(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_smtp_connect(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_storage_writable(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_writable"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL)


# ---------------------------------------------------------------------------
# New check tests — H8 Deployment
# ---------------------------------------------------------------------------


class TestDeploymentChecksNew:
    def test_deploy_drift(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.drift"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_service_state(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.service_state"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_deploy_files(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.files"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_health_endpoint(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.health_endpoint"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_proxy_config(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.proxy"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_bind_address(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.bind"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_stale_pid(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_restart_loop(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.restart_loop"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)


# ---------------------------------------------------------------------------
# New check tests — H9 Backup
# ---------------------------------------------------------------------------


class TestBackupChecksNew:
    def test_backup_manifest(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)

    def test_backup_encryption(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["backup.encryption"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_backup_retention(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["backup.retention"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


# ---------------------------------------------------------------------------
# New check tests — Security
# ---------------------------------------------------------------------------


class TestSecurityChecksNew:
    def test_production_secrets(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["security.secrets"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_cookie_security(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["security.cookie"])
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.WARN)


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestEngineFeatures:
    def test_per_check_timeout(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["db.sqlite_integrity"], total_timeout=120)
            assert len(result.checks) == 1
            assert result.checks[0].status in (CheckStatus.PASS, CheckStatus.SKIP)

    def test_deep_flag(self, app, db):
        with app.app_context():
            result_normal = run_doctor(deep=False)
            result_deep = run_doctor(deep=True)
            assert len(result_deep.checks) >= len(result_normal.checks)

    def test_json_serialization(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
            d = result.to_dict()
            import json

            serialized = json.dumps(d, default=str)
            assert isinstance(serialized, str)
            assert "doctor.ok" in serialized or "doctor.degraded" in serialized or "doctor.failed" in serialized

    def test_total_timeout_skips_remaining(self, app, db):
        with app.app_context():
            result = run_doctor(total_timeout=0.001)
            skipped = [c for c in result.checks if c.status == CheckStatus.SKIP]
            assert len(skipped) > 0 or len(result.checks) == 0

    def test_severity_ordering(self, app, db):
        with app.app_context():
            result = run_doctor()
            assert len(result.checks) > 10
            categories = {c.category for c in result.checks}
            assert "database" in categories
            assert "filesystem" in categories


# ---------------------------------------------------------------------------
# Safe fix tests — new fixes
# ---------------------------------------------------------------------------


class TestNewSafeFixes:
    def test_cleanup_stale_pid_registered(self):
        from app.services.operations.doctor import _SAFE_FIXES

        assert "cleanup_stale_pid" in _SAFE_FIXES

    def test_rebuild_fts_registered(self):
        from app.services.operations.doctor import _SAFE_FIXES

        assert "rebuild_fts" in _SAFE_FIXES

    def test_correct_permissions_registered(self):
        from app.services.operations.doctor import _SAFE_FIXES

        assert "correct_permissions" in _SAFE_FIXES

    def test_fix_create_dirs(self, app, db):
        from app.services.operations.doctor import _fix_create_missing_dirs, CheckResult

        cr = CheckResult("test", "filesystem", "warn", "recommended", "missing", safe_fix_id="create_missing_dirs")
        ok, detail = _fix_create_missing_dirs(cr)
        assert isinstance(ok, bool)
        assert isinstance(detail, str)

    def test_fix_cleanup_stale_pid(self, app, db):
        from app.services.operations.doctor import _fix_cleanup_stale_pid, CheckResult

        cr = CheckResult("test", "deployment", "warn", "optional", "stale", safe_fix_id="cleanup_stale_pid")
        ok, detail = _fix_cleanup_stale_pid(cr)
        assert isinstance(ok, bool)

    def test_fix_rebuild_fts(self, app, db):
        from app.services.operations.doctor import _fix_rebuild_fts, CheckResult

        with app.app_context():
            cr = CheckResult("test", "search", "warn", "recommended", "missing", safe_fix_id="rebuild_fts")
            ok, detail = _fix_rebuild_fts(cr)
            assert isinstance(ok, bool)

    def test_fix_correct_permissions(self, app, db):
        from app.services.operations.doctor import _fix_correct_permissions, CheckResult

        cr = CheckResult("test", "secrets", "warn", "recommended", "permissive", safe_fix_id="correct_permissions")
        ok, detail = _fix_correct_permissions(cr)
        assert isinstance(ok, bool)


# ---------------------------------------------------------------------------
# Broken-state scenario tests
# ---------------------------------------------------------------------------


class TestBrokenStateScenarios:
    def test_missing_secret_key(self, app, db, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.FAIL
            assert "SECRET_KEY" in result.checks[0].summary

    def test_placeholder_secret_key(self, app, db, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "changeme")
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.FAIL
            assert "placeholder" in result.checks[0].summary.lower()

    def test_missing_admin_password(self, app, db, monkeypatch):
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.admin_password"])
            assert result.checks[0].status == CheckStatus.FAIL

    def test_short_secret_key_warns(self, app, db, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "short")
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"])
            assert result.checks[0].status == CheckStatus.WARN

    def test_production_required_enforced(self, app, db, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with app.app_context():
            result = run_doctor(check_ids=["secrets.secret_key"], production=True)
            assert result.checks[0].status == CheckStatus.FAIL
            assert result.ok is False

    def test_single_check_failure_does_not_block_others(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["nonexistent.check", "pkg.version"])
            pkg_results = [c for c in result.checks if c.check_id == "pkg.version"]
            assert len(pkg_results) == 1
            assert pkg_results[0].status == CheckStatus.PASS

    def test_check_id_not_found_returns_empty(self, app, db):
        with app.app_context():
            result = run_doctor(check_ids=["totally.nonexistent.id"])
            assert len(result.checks) == 0

    def test_category_filter(self, app, db):
        with app.app_context():
            result = run_doctor(category="nonexistent")
            assert len(result.checks) == 0
            assert result.ok is True
