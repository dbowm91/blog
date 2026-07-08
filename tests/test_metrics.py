import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from unittest.mock import patch


class TestMetricsPublic:
    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_public_when_no_secrets(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_public_returns_content(self, client, db):
        resp = client.get("/metrics")
        data = resp.get_data(as_text=True)
        assert "blog_health_status" in data or "blog_requests_total" in data


class TestMetricsWithMetricsSecret:
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_requires_secret_when_metrics_secret_set(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_wrong_secret_returns_401(self, client, db):
        resp = client.get("/metrics?secret=wrong")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-pass-42")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "")
    def test_correct_secret_returns_200(self, client, db):
        resp = client.get("/metrics?secret=metrics-pass-42")
        assert resp.status_code == 200


class TestMetricsFallbackToHealthSecret:
    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "health-pass-99")
    def test_falls_back_to_health_check_secret(self, client, db):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "health-pass-99")
    def test_wrong_health_secret_returns_401(self, client, db):
        resp = client.get("/metrics?secret=wrong")
        assert resp.status_code == 401

    @patch("app.routes.public.meta.METRICS_SECRET", "")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "health-pass-99")
    def test_correct_health_secret_returns_200(self, client, db):
        resp = client.get("/metrics?secret=health-pass-99")
        assert resp.status_code == 200


class TestMetricsSecretPrecedence:
    @patch("app.routes.public.meta.METRICS_SECRET", "metrics-val")
    @patch("app.routes.public.meta.HEALTH_CHECK_SECRET", "health-val")
    def test_metrics_secret_takes_precedence(self, client, db):
        resp = client.get("/metrics?secret=health-val")
        assert resp.status_code == 401

        resp = client.get("/metrics?secret=metrics-val")
        assert resp.status_code == 200
