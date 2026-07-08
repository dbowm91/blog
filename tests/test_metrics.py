import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from unittest.mock import patch


class TestMetricsDisabled:
    @patch("app.routes.public.meta.ENABLE_METRICS", False)
    def test_returns_404_when_disabled(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not found"


class TestMetricsPublic:
    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "")
    def test_public_when_no_secret(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "")
    def test_public_returns_content(self, client, db):
        resp = client.get("/metrics")
        data = resp.get_data(as_text=True)
        assert "blog_health_status" in data or "blog_requests_total" in data


class TestMetricsWithMetricsSecret:
    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_requires_secret_when_metrics_secret_set(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_wrong_secret_returns_401(self, client, db):
        resp = client.get("/metrics?secret=wrong")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_correct_query_secret_returns_200(self, client, db):
        resp = client.get("/metrics?secret=metrics-pass-42")
        assert resp.status_code == 200

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_correct_header_secret_returns_200(self, client, db):
        resp = client.get(
            "/metrics",
            headers={"X-Metrics-Secret": "metrics-pass-42"},
        )
        assert resp.status_code == 200

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_correct_bearer_token_returns_200(self, client, db):
        resp = client.get(
            "/metrics",
            headers={"Authorization": "Bearer metrics-pass-42"},
        )
        assert resp.status_code == 200

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    def test_wrong_header_returns_401(self, client, db):
        resp = client.get(
            "/metrics",
            headers={"X-Metrics-Secret": "wrong"},
        )
        assert resp.status_code == 401


class TestMetricsProductionRequired:
    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.is_production", return_value=True)
    def test_returns_403_when_no_secret_in_production(self, mock_prod, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 403
        assert "METRICS_SECRET required" in resp.get_json()["error"]

    @patch("app.routes.public.meta.ENABLE_METRICS", True)
    @patch("app.routes.public.meta.METRICS_SECRET", "prod-secret")
    @patch("app.routes.public.meta.is_production", return_value=True)
    def test_with_secret_works_in_production(self, mock_prod, client, db):
        resp = client.get(
            "/metrics",
            headers={"X-Metrics-Secret": "prod-secret"},
        )
        assert resp.status_code == 200
