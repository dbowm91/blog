from __future__ import annotations

from urllib.parse import urlparse

from app.deployment.model import DeploymentContext, RenderResult


def _extract_hostname(public_url: str) -> str:
    parsed = urlparse(public_url)
    host = parsed.hostname or ""
    if not host:
        return "localhost"
    return host


def _extract_scheme(public_url: str) -> str:
    parsed = urlparse(public_url)
    return (parsed.scheme or "http").lower()


def _extract_port(public_url: str) -> int | None:
    parsed = urlparse(public_url)
    return parsed.port


def _upload_size_mb(ctx: DeploymentContext) -> int:
    return max(1, ctx.config.app.max_upload_size // (1024 * 1024))


def _proxy_warnings(ctx: DeploymentContext) -> list[str]:
    warnings: list[str] = []
    hostname = _extract_hostname(ctx.public_url)
    if hostname in ("localhost", "127.0.0.1", "::1") and ctx.bind_address == "0.0.0.0":
        warnings.append(
            "Public URL points to localhost but bind address is 0.0.0.0; "
            "remote clients will not be able to connect via the public URL."
        )
    scheme = _extract_scheme(ctx.public_url)
    if scheme == "https" and ctx.bind_address == "0.0.0.0":
        warnings.append("Public URL uses HTTPS. Ensure TLS termination is handled by the proxy.")
    return warnings


def render_caddyfile(ctx: DeploymentContext) -> RenderResult:
    hostname = _extract_hostname(ctx.public_url)
    scheme = _extract_scheme(ctx.public_url)
    public_port = _extract_port(ctx.public_url)
    upstream = f"http://{ctx.bind_address}:{ctx.bind_port}"
    upload_mb = _upload_size_mb(ctx)
    warnings = _proxy_warnings(ctx)

    lines: list[str] = []

    if scheme == "https" or (scheme == "http" and public_port not in (80, None)):
        listen = f":{public_port or 443}" if public_port else ":443"
    else:
        listen = ":80"

    lines.append(f"{hostname}{listen} {{")

    if scheme == "https":
        lines.append("    tls {")
        lines.append("    }")

    lines.append("")
    lines.append("    request_body {")
    lines.append(f"        max_size {upload_mb}MB")
    lines.append("    }")
    lines.append("")

    lines.append("    @health path /health")
    lines.append("    log @health {")
    lines.append("        output discard")
    lines.append("    }")
    lines.append("")

    lines.append("    header {")
    lines.append("        X-Forwarded-For {remote_host}")
    lines.append("        X-Forwarded-Proto {scheme}")
    lines.append("        X-Forwarded-Host {host}")
    lines.append("        X-Content-Type-Options nosniff")
    lines.append("        X-Frame-Options DENY")
    lines.append("        X-XSS-Protection 1; mode=block")
    lines.append("        Referrer-Policy strict-origin-when-cross-origin")
    lines.append("        -Server")
    lines.append("    }")
    lines.append("")

    lines.append("    encode gzip zstd")
    lines.append("")

    lines.append("    proxy * {")
    lines.append(f"        to {upstream}")
    lines.append("        header_up X-Forwarded-For {remote_host}")
    lines.append("        header_up X-Forwarded-Proto {scheme}")
    lines.append("        header_up X-Forwarded-Host {host}")
    lines.append("    }")
    lines.append("")

    lines.append(
        "    @attachment path_regexp attachment ^/(static/)?uploads/[0-9a-f]{32}-[^/]+\\.attachment$"
    )
    lines.append('    header @attachment Content-Disposition "attachment"')
    lines.append('    header @attachment X-Content-Type-Options "nosniff"')
    lines.append('    header @attachment Cache-Control "private, no-store"')
    lines.append("")
    lines.append("    @static path /static/uploads/*")
    lines.append("    handle @static {")
    lines.append(f"        root * {ctx.paths.uploads_dir.path}")
    lines.append("        uri strip_prefix /static/uploads")
    lines.append("        file_server")
    lines.append("    }")
    lines.append("")
    lines.append("    @legacy_uploads path /uploads/*")
    lines.append("    handle @legacy_uploads {")
    lines.append(f"        root * {ctx.paths.uploads_dir.path}")
    lines.append("        uri strip_prefix /uploads")
    lines.append("        file_server")
    lines.append("    }")
    lines.append("")

    lines.append("}")

    content = "\n".join(lines) + "\n"

    warnings.append(
        "Caddy has no built-in rate limiting. The application deliberately does not "
        "rate limit the login routes, so this proxy needs a rate limiting plugin "
        "(for example caddy-ratelimit) or a WAF in front of it."
    )

    return RenderResult(
        content=content,
        filename="Caddyfile",
        target="caddy",
        managed=True,
        warnings=warnings,
        permissions=0o644,
        description="Caddy reverse proxy configuration",
    )


def render_nginx_config(ctx: DeploymentContext) -> RenderResult:
    hostname = _extract_hostname(ctx.public_url)
    scheme = _extract_scheme(ctx.public_url)
    public_port = _extract_port(ctx.public_url)
    upstream_addr = ctx.bind_address
    upstream_port = ctx.bind_port
    upload_mb = _upload_size_mb(ctx)
    warnings = _proxy_warnings(ctx)

    lines: list[str] = []

    lines.append("# Include this file from the http context: the limit_req_zone")
    lines.append("# directives below are only valid there.")
    lines.append("limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;")
    lines.append("limit_req_zone $binary_remote_addr zone=admin:10m rate=20r/m;")
    lines.append("")

    lines.append("upstream devlog_backend {")
    lines.append(f"    server {upstream_addr}:{upstream_port};")
    lines.append("    keepalive 32;")
    lines.append("}")
    lines.append("")

    if scheme == "https":
        listen_port = public_port or 443
        lines.append("server {")
        lines.append(f"    listen {listen_port} ssl http2;")
        lines.append(f"    server_name {hostname};")
        lines.append("")
        lines.append("    ssl_certificate     /etc/ssl/devlog/cert.pem;")
        lines.append("    ssl_certificate_key /etc/ssl/devlog/key.pem;")
        lines.append("    ssl_protocols       TLSv1.2 TLSv1.3;")
        lines.append("    ssl_ciphers         HIGH:!aNULL:!MD5;")
        lines.append("    ssl_prefer_server_ciphers on;")
    else:
        listen_port = public_port or 80
        lines.append("server {")
        lines.append(f"    listen {listen_port};")
        lines.append(f"    server_name {hostname};")

    lines.append("")
    lines.append(f"    client_max_body_size {upload_mb}M;")
    lines.append("")
    lines.append("    proxy_read_timeout 60s;")
    lines.append("    proxy_connect_timeout 10s;")
    lines.append("    proxy_send_timeout 60s;")
    lines.append("")
    lines.append("    proxy_set_header Host              $host;")
    lines.append("    proxy_set_header X-Real-IP         $remote_addr;")
    lines.append("    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;")
    lines.append("    proxy_set_header X-Forwarded-Proto $scheme;")
    lines.append("    proxy_set_header X-Forwarded-Host  $host;")
    lines.append("")
    lines.append("    gzip on;")
    lines.append("    gzip_vary on;")
    lines.append("    gzip_proxied any;")
    lines.append("    gzip_comp_level 6;")
    lines.append(
        "    gzip_types text/plain text/css application/json application/javascript "
        "text/xml application/xml application/xml+rss text/javascript;"
    )
    lines.append("")
    lines.append("    add_header X-Content-Type-Options nosniff always;")
    lines.append("    add_header X-Frame-Options DENY always;")
    lines.append('    add_header X-XSS-Protection "1; mode=block" always;')
    lines.append("    add_header Referrer-Policy strict-origin-when-cross-origin always;")
    lines.append("")
    lines.append(r"    location ~ ^/(static/)?uploads/([0-9a-f]{32}-[^/]+\.attachment)$ {")
    lines.append(f"        alias {ctx.paths.uploads_dir.path}/$2;")
    lines.append("        default_type application/octet-stream;")
    lines.append('        add_header Content-Disposition "attachment" always;')
    lines.append("        add_header X-Content-Type-Options nosniff always;")
    lines.append('        add_header Cache-Control "private, no-store" always;')
    lines.append("    }")
    lines.append("")
    lines.append("    location /static/uploads/ {")
    lines.append(f"        alias {ctx.paths.uploads_dir.path}/;")
    lines.append("        expires 30d;")
    lines.append('        add_header Cache-Control "public, immutable";')
    lines.append("    }")
    lines.append("")
    lines.append("    location /uploads/ {")
    lines.append(f"        alias {ctx.paths.uploads_dir.path}/;")
    lines.append("        expires 30d;")
    lines.append('        add_header Cache-Control "public, immutable";')
    lines.append("    }")
    lines.append("")

    lines.append("    location /health {")
    lines.append("        access_log off;")
    lines.append("        proxy_pass http://devlog_backend;")
    lines.append("    }")
    lines.append("")

    lines.append("    # Login rate limiting. The application does not rate limit the")
    lines.append("    # login routes; the proxy is the place for it.")
    for login_path in ("/login", "/admin/login"):
        lines.append(f"    location = {login_path} {{")
        lines.append("        limit_req zone=login burst=5 nodelay;")
        lines.append("        limit_req_status 429;")
        lines.append("        proxy_pass http://devlog_backend;")
        lines.append("        proxy_set_header Host              $host;")
        lines.append("        proxy_set_header X-Real-IP         $remote_addr;")
        lines.append("        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;")
        lines.append("        proxy_set_header X-Forwarded-Proto $scheme;")
        lines.append("    }")
        lines.append("")

    lines.append("    location / {")
    lines.append("        proxy_pass http://devlog_backend;")
    lines.append("        proxy_set_header Host              $host;")
    lines.append("        proxy_set_header X-Real-IP         $remote_addr;")
    lines.append("        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;")
    lines.append("        proxy_set_header X-Forwarded-Proto $scheme;")
    lines.append("    }")
    lines.append("")

    lines.append("}")

    content = "\n".join(lines) + "\n"

    return RenderResult(
        content=content,
        filename="devlog.conf",
        target="nginx",
        managed=True,
        warnings=warnings,
        permissions=0o644,
        description="nginx reverse proxy configuration (include from the http context)",
    )


def validate_caddyfile(content: str) -> list[str]:
    errors: list[str] = []
    brace_count = 0
    for line_no, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        brace_count += stripped.count("{") - stripped.count("}")
        if brace_count < 0:
            errors.append(f"Unmatched closing brace at line {line_no}")
            break
    if brace_count != 0:
        errors.append(f"Unmatched braces: {brace_count} unclosed block(s)")
    blocks = 0
    for line_no, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.endswith("{"):
            blocks += 1
    if blocks == 0 and content.strip():
        errors.append("No blocks found; expected at least one site block")
    return errors


def validate_nginx_config(content: str) -> list[str]:
    errors: list[str] = []
    brace_count = 0
    for line_no, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        brace_count += stripped.count("{") - stripped.count("}")
        if brace_count < 0:
            errors.append(f"Unmatched closing brace at line {line_no}")
            break
    if brace_count != 0:
        errors.append(f"Unmatched braces: {brace_count} unclosed block(s)")
    for line_no, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("server ") or stripped.startswith("upstream "):
            if "{" not in stripped and not stripped.endswith("{"):
                errors.append(f"Missing opening brace for directive at line {line_no}")
        if stripped.startswith("listen ") or stripped.startswith("server_name "):
            if not stripped.endswith(";"):
                errors.append(f"Missing semicolon at line {line_no}")
    return errors
