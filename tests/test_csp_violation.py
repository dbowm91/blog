import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from app.csrf import should_skip_csrf


class TestCspViolationCsrfExemption:
    def test_report_path_skips_csrf(self, app):
        with app.test_request_context("/csp-violation", method="POST"):
            assert should_skip_csrf()

    def test_other_post_paths_do_not_skip(self, app):
        with app.test_request_context("/admin/new", method="POST"):
            assert not should_skip_csrf()


class TestCspViolation:
    def test_report_accepted_without_csrf_token(self, client, db):
        resp = client.post(
            "/csp-violation",
            json={
                "csp-report": {
                    "document-uri": "http://example.com/",
                    "violated-directive": "style-src-attr",
                    "blocked-uri": "inline",
                }
            },
        )
        assert resp.status_code == 204

    def test_report_accepts_csp_report_content_type(self, client, db):
        resp = client.post(
            "/csp-violation",
            data='{"csp-report":{"violated-directive":"script-src-attr"}}',
            content_type="application/csp-report",
        )
        assert resp.status_code == 204

    def test_report_logs_violation_details(self, client, db, caplog):
        with caplog.at_level("INFO", logger="app.routes.public.meta"):
            client.post(
                "/csp-violation",
                data='{"csp-report":{"violated-directive":"style-src-attr","blocked-uri":"inline"}}',
                content_type="application/csp-report",
            )
        assert "style-src-attr" in caplog.text
        assert "blocked=inline" in caplog.text

    def test_report_tolerates_empty_body(self, client, db):
        resp = client.post("/csp-violation", data="", content_type="application/csp-report")
        assert resp.status_code == 204

    def test_report_rejects_oversized_body(self, client, db):
        resp = client.post(
            "/csp-violation",
            data="x" * (64 * 1024 + 1),
            content_type="application/csp-report",
        )
        assert resp.status_code == 413

    def test_report_get_not_allowed(self, client, db):
        resp = client.get("/csp-violation")
        assert resp.status_code == 405
