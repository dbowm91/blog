import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from unittest.mock import patch


class TestHealthBasic:
    def test_basic_returns_only_database_and_scheduler(self, client, db):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data["checks"].keys()) == {"database", "scheduler"}

    def test_basic_database_ok(self, client, db):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["checks"]["database"] == "ok"

    def test_basic_scheduler_status(self, client, db):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["checks"]["scheduler"] in ("running", "disabled", "stopped")

    def test_basic_has_timestamp(self, client, db):
        resp = client.get("/health")
        data = resp.get_json()
        assert "timestamp" in data

    def test_basic_does_not_include_detailed_checks(self, client, db):
        resp = client.get("/health")
        data = resp.get_json()
        for key in ("search", "disk_space", "db_integrity", "redis", "celery", "backup_freshness"):
            assert key not in data["checks"]


class TestHealthDetailedNoSecret:
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_detailed_no_secret_returns_all_checks(self, client, db):
        resp = client.get("/health?detailed=true")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "database" in data["checks"]
        assert "scheduler" in data["checks"]
        assert "search" in data["checks"]
        assert "disk_space" in data["checks"]
        assert "db_integrity" in data["checks"]

    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_detailed_no_secret_has_details(self, client, db):
        resp = client.get("/health?detailed=true")
        data = resp.get_json()
        assert "details" in data
        assert "database_latency_ms" in data["details"]


class TestHealthDetailedWithSecret:
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "my-secret-123")
    def test_detailed_without_secret_returns_401(self, client, db):
        resp = client.get("/health?detailed=true")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "unauthorized"

    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "my-secret-123")
    def test_detailed_with_wrong_secret_returns_401(self, client, db):
        resp = client.get("/health?detailed=true&secret=wrong-secret")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "my-secret-123")
    def test_detailed_with_correct_secret_returns_all_checks(self, client, db):
        resp = client.get("/health?detailed=true&secret=my-secret-123")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "database" in data["checks"]
        assert "scheduler" in data["checks"]
        assert "search" in data["checks"]
        assert "disk_space" in data["checks"]
        assert "db_integrity" in data["checks"]
        assert "details" in data

    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "my-secret-123")
    def test_basic_still_works_without_secret_when_secret_required(self, client, db):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data["checks"].keys()) == {"database", "scheduler"}
