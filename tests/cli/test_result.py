import json
import io
from devlog_cli.result import Result
from devlog_cli.errors import (
    DevlogError,
    ConfigError,
    DatabaseError,
    ServiceError,
    BackupError,
    MissingDependencyError,
)
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render_human, render_json, render


class TestResult:
    def test_success_factory(self):
        r = Result.success(code="test.ok", summary="All good")
        assert r.ok is True
        assert r.status == "success"
        assert r.code == "test.ok"
        assert r.summary == "All good"
        assert r.exit_code == ExitCode.SUCCESS

    def test_failure_factory(self):
        r = Result.failure(code="test.fail", summary="Nope")
        assert r.ok is False
        assert r.status == "failure"
        assert r.exit_code == ExitCode.GENERAL_FAILURE

    def test_failure_custom_exit_code(self):
        r = Result.failure(code="test.fail", summary="Nope", exit_code=ExitCode.DATABASE_ERROR)
        assert r.exit_code == ExitCode.DATABASE_ERROR

    def test_degraded_factory(self):
        r = Result.degraded(code="test.deg", summary="Partial")
        assert r.ok is False
        assert r.status == "degraded"
        assert r.exit_code == ExitCode.DEGRADED

    def test_to_dict(self):
        r = Result.success(code="x", summary="y", details={"k": "v"}, warnings=["w1"])
        d = r.to_dict()
        assert d["ok"] is True
        assert d["details"] == {"k": "v"}
        assert d["warnings"] == ["w1"]

    def test_remediation_in_dict(self):
        r = Result.success(code="x", summary="y", remediation=["do this"])
        d = r.to_dict()
        assert "remediation" in d
        assert d["remediation"] == ["do this"]

    def test_no_remediation_omitted(self):
        r = Result.success(code="x", summary="y")
        d = r.to_dict()
        assert "remediation" not in d

    def test_to_json(self):
        r = Result.success(code="x", summary="y")
        j = r.to_json()
        data = json.loads(j)
        assert data["ok"] is True

    def test_to_json_pretty(self):
        r = Result.success(code="x", summary="y")
        j = r.to_json(indent=2)
        assert "\n" in j


class TestExitCodes:
    def test_all_codes_are_integers(self):
        for code in ExitCode:
            assert isinstance(code, int)

    def test_success_is_zero(self):
        assert ExitCode.SUCCESS == 0

    def test_distinct_codes(self):
        codes = [c.value for c in ExitCode]
        assert len(codes) == len(set(codes))


class TestErrors:
    def test_base_exception(self):
        e = DevlogError("test")
        assert str(e) == "test"
        assert e.exit_code == ExitCode.GENERAL_FAILURE

    def test_config_error(self):
        e = ConfigError("bad config")
        assert e.exit_code == ExitCode.INVALID_CONFIG

    def test_database_error(self):
        e = DatabaseError("db down")
        assert e.exit_code == ExitCode.DATABASE_ERROR

    def test_service_error(self):
        e = ServiceError("svc down")
        assert e.exit_code == ExitCode.SERVICE_ERROR

    def test_backup_error(self):
        e = BackupError("backup failed")
        assert e.exit_code == ExitCode.BACKUP_ERROR

    def test_missing_dependency_error(self):
        e = MissingDependencyError("missing")
        assert e.exit_code == ExitCode.MISSING_DEPENDENCY

    def test_error_with_remediation(self):
        e = DevlogError("err", remediation="fix it")
        assert e.remediation == "fix it"


class TestOutput:
    def test_render_human_success(self):
        r = Result.success(code="x", summary="OK")
        buf = io.StringIO()
        render_human(r, file=buf)
        assert "OK" in buf.getvalue()

    def test_render_human_failure(self):
        r = Result.failure(code="x", summary="Failed")
        buf = io.StringIO()
        render_human(r, file=buf)
        assert "Error: Failed" in buf.getvalue()

    def test_render_human_verbose(self):
        r = Result.success(code="x", summary="OK", warnings=["w1"], remediation=["r1"])
        buf = io.StringIO()
        render_human(r, verbose=True, file=buf)
        out = buf.getvalue()
        assert "w1" in out
        assert "r1" in out

    def test_render_json(self):
        r = Result.success(code="x", summary="OK")
        buf = io.StringIO()
        render_json(r, file=buf)
        data = json.loads(buf.getvalue())
        assert data["ok"] is True

    def test_render_json_mode(self):
        r = Result.success(code="x", summary="OK")
        buf = io.StringIO()
        render(r, json_mode=True, file=buf)
        data = json.loads(buf.getvalue())
        assert data["ok"] is True

    def test_render_human_mode(self):
        r = Result.success(code="x", summary="OK")
        buf = io.StringIO()
        render(r, json_mode=False, file=buf)
        assert "OK" in buf.getvalue()
