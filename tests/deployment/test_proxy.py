from __future__ import annotations

from app.config.model import DevLogConfig, ServerConfig, SiteConfig
from app.deployment.model import DeploymentContext
from app.deployment.proxy import (
    render_caddyfile,
    render_nginx_config,
    validate_caddyfile,
    validate_nginx_config,
)
from app.filesystem.layout import InstallMode


def _make_ctx(app, *, base_url="http://localhost:5000", host="127.0.0.1", port=5000):
    config = DevLogConfig(
        site=SiteConfig(base_url=base_url),
        server=ServerConfig(host=host, port=port),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.DOCKER)


class TestRenderCaddyfile:
    def test_basic_structure(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert result.filename == "Caddyfile"
        assert result.managed is True
        assert "example.com" in result.content

    def test_https_listen_directive(self, app):
        ctx = _make_ctx(app, base_url="https://example.com")
        result = render_caddyfile(ctx)
        assert "tls" in result.content

    def test_http_listen_directive(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert ":80" in result.content

    def test_hostname_extracted(self, app):
        ctx = _make_ctx(app, base_url="https://blog.example.com:8443")
        result = render_caddyfile(ctx)
        assert "blog.example.com" in result.content

    def test_upload_size_limit(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "max_size" in result.content
        assert "MB" in result.content

    def test_security_headers(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "X-Content-Type-Options" in result.content
        assert "X-Frame-Options" in result.content
        assert "X-XSS-Protection" in result.content
        assert "Referrer-Policy" in result.content

    def test_proxy_upstream(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "proxy *" in result.content
        assert "127.0.0.1:5000" in result.content

    def test_encode_gzip(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "encode gzip" in result.content

    def test_file_server_uploads(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "file_server" in result.content
        assert "/uploads/" in result.content

    def test_health_path_logging_disabled(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert "@health" in result.content
        assert "output discard" in result.content


class TestRenderNginxConfig:
    def test_basic_structure(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert result.filename == "devlog.conf"
        assert result.managed is True

    def test_upstream_definition(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "upstream devlog_backend" in result.content
        assert "keepalive 32" in result.content

    def test_https_listen(self, app):
        ctx = _make_ctx(app, base_url="https://example.com")
        result = render_nginx_config(ctx)
        assert "ssl" in result.content
        assert "http2" in result.content

    def test_http_listen(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "listen 80" in result.content

    def test_ssl_config(self, app):
        ctx = _make_ctx(app, base_url="https://example.com")
        result = render_nginx_config(ctx)
        assert "ssl_certificate" in result.content
        assert "ssl_protocols" in result.content

    def test_proxy_headers(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "X-Real-IP" in result.content
        assert "X-Forwarded-For" in result.content
        assert "X-Forwarded-Proto" in result.content

    def test_gzip_settings(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "gzip on" in result.content
        assert "gzip_vary on" in result.content
        assert "gzip_comp_level" in result.content

    def test_security_headers(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "X-Content-Type-Options" in result.content
        assert "X-Frame-Options" in result.content
        assert "Referrer-Policy" in result.content

    def test_client_max_body_size(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "client_max_body_size" in result.content

    def test_uploads_location(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "location /uploads/" in result.content

    def test_health_location(self, app):
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "location /health" in result.content
        assert "access_log off" in result.content

    def test_login_locations_are_rate_limited(self, app):
        """Both login entry points carry the proxy-side limit."""
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert "limit_req_zone $binary_remote_addr zone=login" in result.content
        assert "location = /login {" in result.content
        assert "location = /admin/login {" in result.content
        assert result.content.count("limit_req zone=login") == 2

    def test_login_limit_is_declared_before_the_server_block(self, app):
        """limit_req_zone is only valid in the http context."""
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_nginx_config(ctx)
        assert result.content.index("limit_req_zone") < result.content.index("server {")


class TestShippedNginxConfig:
    """The nginx configuration that ships with the repository."""

    def _config(self) -> str:
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "nginx" / "conf.d" / "blog.conf"
        return path.read_text()

    def test_public_login_is_rate_limited(self):
        assert "location = /login {" in self._config()

    def test_admin_login_is_rate_limited(self):
        assert "location = /admin/login {" in self._config()

    def test_login_limit_uses_the_login_zone(self):
        content = self._config()
        assert content.count("limit_req zone=login") == 2

    def test_nginx_conf_defines_the_login_zone(self):
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "nginx" / "nginx.conf"
        content = path.read_text()
        assert "zone=login:10m rate=5r/m;" in content


class TestValidateCaddyfile:
    def test_valid_caddyfile_no_errors(self):
        content = """example.com:80 {
    proxy * http://127.0.0.1:5000
}
"""
        errors = validate_caddyfile(content)
        assert errors == []

    def test_unmatched_opening_brace(self):
        content = """example.com:80 {
    proxy * http://127.0.0.1:5000
"""
        errors = validate_caddyfile(content)
        assert any("unclosed" in e for e in errors)

    def test_unmatched_closing_brace(self):
        content = """example.com:80 }
    proxy * http://127.0.0.1:5000
"""
        errors = validate_caddyfile(content)
        assert any("Unmatched closing brace" in e for e in errors)

    def test_no_blocks_found(self):
        content = """# just a comment
"""
        errors = validate_caddyfile(content)
        assert any("No blocks found" in e for e in errors)

    def test_multiple_blocks(self):
        content = """example.com:80 {
    proxy * http://127.0.0.1:5000
}

other.com:80 {
    proxy * http://127.0.0.1:5001
}
"""
        errors = validate_caddyfile(content)
        assert errors == []


class TestValidateNginxConfig:
    def test_valid_nginx_no_errors(self):
        content = """upstream devlog_backend {
    keepalive 32;
}

server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://devlog_backend;
    }
}
"""
        errors = validate_nginx_config(content)
        assert errors == []

    def test_unmatched_braces(self):
        content = """upstream devlog_backend {
    keepalive 32;

server {
    listen 80;
    server_name example.com;
}
"""
        errors = validate_nginx_config(content)
        assert any("unclosed" in e for e in errors)

    def test_missing_semicolon(self):
        content = """server {
    listen 80
    server_name example.com;
}
"""
        errors = validate_nginx_config(content)
        assert any("Missing semicolon" in e for e in errors)

    def test_comments_ignored(self):
        content = """# upstream devlog_backend {
#     keepalive 32;
# }
server {
    listen 80;
    server_name example.com;
}
"""
        errors = validate_nginx_config(content)
        assert errors == []


class TestProxyWarnings:
    def test_localhost_with_0_0_0_bind_warns(self, app):
        config = DevLogConfig(
            site=SiteConfig(base_url="http://localhost:5000"),
            server=ServerConfig(host="0.0.0.0", port=5000),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_caddyfile(ctx)
        assert any("localhost" in w.lower() for w in result.warnings)

    def test_https_with_0_0_0_bind_warns(self, app):
        config = DevLogConfig(
            site=SiteConfig(base_url="https://example.com"),
            server=ServerConfig(host="0.0.0.0", port=5000),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_caddyfile(ctx)
        assert any("HTTPS" in w for w in result.warnings)

    def test_no_warning_for_normal_setup(self, app):
        config = DevLogConfig(
            site=SiteConfig(base_url="http://example.com"),
            server=ServerConfig(host="127.0.0.1", port=5000),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_caddyfile(ctx)
        other = [w for w in result.warnings if "rate limiting" not in w.lower()]
        assert other == []

    def test_caddy_warns_about_the_missing_rate_limiter(self, app):
        """Caddy has no built-in rate limiting and the application has none either."""
        ctx = _make_ctx(app, base_url="http://example.com")
        result = render_caddyfile(ctx)
        assert any("rate limiting" in w.lower() for w in result.warnings)

    def test_nginx_localhost_warning(self, app):
        config = DevLogConfig(
            site=SiteConfig(base_url="http://localhost:5000"),
            server=ServerConfig(host="0.0.0.0", port=5000),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_nginx_config(ctx)
        assert any("localhost" in w.lower() for w in result.warnings)
