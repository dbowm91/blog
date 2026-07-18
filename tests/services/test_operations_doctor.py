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
