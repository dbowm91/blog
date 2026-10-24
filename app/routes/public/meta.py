"""Meta routes - robots.txt, sitemap.xml, favicon, health check, metrics."""

import hmac
import logging
import time
import shutil
from pathlib import Path
from typing import Any
from flask import current_app

from flask import (
    url_for,
    request,
    jsonify,
    Response,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import db
from app.models import Post, Tag, Page, User
from app.config import (
    BASE_URL,
    HEALTH_CHECK_SECRET,
    METRICS_SECRET,
    ENABLE_METRICS,
    REDIS_URL,
    DATA_BACKUP_DIR,
    is_production,
)
from app.scheduler import get_scheduler_health
from app.utils import xml_escape, utc_now
from app import limiter
from app.db_utils import is_sqlite_database

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


def _provided_secret(header_name: str) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    return request.headers.get(header_name, "") or request.args.get("secret", "")


def _secret_matches(expected: str, header_name: str) -> bool:
    if not expected:
        return False
    provided = _provided_secret(header_name)
    return bool(provided) and hmac.compare_digest(provided, expected)


def _generate_sitemap():
    """Generate sitemap XML as a generator."""
    yield '<?xml version="1.0" encoding="UTF-8"?>\n'
    yield '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Homepage
    yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""
    # Archive page
    yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/archive</loc>
    <changefreq>weekly</changefreq>
    <priority>0.5</priority>
  </url>\n"""
    # Static pages
    for pg in (
        db.session.execute(select(Page).filter_by(published=True).order_by(Page.updated_at.desc()))
        .scalars()
        .yield_per(100)
    ):
        lastmod = pg.updated_at.strftime("%Y-%m-%d") if pg.updated_at else ""
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/page/{xml_escape(pg.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>\n"""
    # Posts
    for post in (
        db.session.execute(select(Post).filter_by(published=True).order_by(Post.updated_at.desc()))
        .scalars()
        .yield_per(100)
    ):
        lastmod = post.updated_at.strftime("%Y-%m-%d") if post.updated_at else ""
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/post/{xml_escape(post.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
    # Author pages
    for username in (
        db.session.execute(
            select(User.username)
            .join(Post, Post.author_id == User.id)
            .filter(Post.published.is_(True))
            .distinct()
            .order_by(User.username)
        )
        .scalars()
        .all()
    ):
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/author/{xml_escape(username)}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>\n"""
    # Tags
    for tag in db.session.execute(select(Tag)).scalars().yield_per(100):
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/tag/{xml_escape(tag.slug)}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>\n"""
    yield "</urlset>\n"


def register_meta_routes(public):
    """Register meta routes on the Blueprint."""

    @public.route("/robots.txt")
    @limiter.limit("60 per minute")
    def robots_txt() -> ResponseReturnValue:
        """Serve robots.txt with sitemap URL and AI crawler blocking."""
        content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /static/uploads/

User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: DuckDuckBot
Disallow: /

User-agent: ia_aggregator
Disallow: /

User-agent: ImagesiftBot
Disallow: /

User-agent: img2dataset
Disallow: /

User-agent: Kraken
Disallow: /

User-agent: Orbisk
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Pileager
Disallow: /

User-agent: Seek
Disallow: /

User-agent: Sitebot
Disallow: /

User-agent: TikTokBot
Disallow: /

User-agent: Turpom
Disallow: /

User-agent: Vercel/Analytics
Disallow: /

User-agent: YouBot
Disallow: /

Sitemap: {BASE_URL}/sitemap.xml
"""
        return Response(content, mimetype="text/plain")

    @public.route("/sitemap.xml")
    @limiter.limit("60 per minute")
    def sitemap_xml() -> ResponseReturnValue:
        """Stream sitemap XML for all published posts, pages, and tags."""
        return Response(_generate_sitemap(), mimetype="application/xml")

    @public.route("/favicon.ico")
    @limiter.limit("60 per minute")
    def favicon() -> ResponseReturnValue:
        """Redirect to SVG favicon."""
        return Response(
            status=302, headers={"Location": url_for("static", filename="img/favicon.svg")}
        )

    @public.route("/health")
    @limiter.limit("60 per minute")
    def health_check() -> ResponseReturnValue:
        """Health check endpoint for monitoring.

        Basic mode (default): Only database and scheduler checks. Safe for Docker healthchecks.
        Detailed mode (?detailed=true): All checks including disk, integrity, redis, celery, backup.
        Requires valid secret when HEALTH_CHECK_SECRET is configured.
        In production without HEALTH_CHECK_SECRET, detailed mode returns 403.
        """
        detailed = request.args.get("detailed", "").lower() == "true"
        status_code = 200

        if detailed:
            if HEALTH_CHECK_SECRET:
                if not _secret_matches(HEALTH_CHECK_SECRET, "X-Health-Secret"):
                    return jsonify({"error": "unauthorized"}), 401
            elif is_production():
                return jsonify({"error": "disabled"}), 403

            checks = {}

            db_start = time.perf_counter()
            try:
                db.session.execute(text("SELECT 1"))
                db_latency_ms = (time.perf_counter() - db_start) * 1000
                checks["database"] = "ok"
            except (OperationalError, ProgrammingError):
                db_latency_ms = (time.perf_counter() - db_start) * 1000
                checks["database"] = "error"
                status_code = 503

            health = get_scheduler_health()
            checks["scheduler"] = health["status"]

            if is_sqlite_database():
                try:
                    has_fts = db.session.execute(
                        text(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
                        )
                    ).fetchone()
                    checks["search"] = "ok" if has_fts else "unavailable"
                except (OperationalError, ProgrammingError):
                    checks["search"] = "error"
            else:
                checks["search"] = "unsupported"

            try:
                from app.config.loader import load_effective_config

                disk_cfg = load_effective_config()
                data_dir_str = disk_cfg.paths.data_dir if disk_cfg.paths.data_dir else None
                disk_path = Path(data_dir_str) if data_dir_str else Path.cwd() / "data"
                disk_usage = shutil.disk_usage(disk_path)
                free_percent = (disk_usage.free / disk_usage.total) * 100
                checks["disk_space"] = "ok" if free_percent >= 10 else "low"
            except OSError:
                checks["disk_space"] = "error"

            if is_sqlite_database():
                try:
                    integrity_result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
                    checks["db_integrity"] = (
                        "ok" if integrity_result and integrity_result[0] == "ok" else "error"
                    )
                except (OperationalError, ProgrammingError):
                    checks["db_integrity"] = "error"
            else:
                checks["db_integrity"] = "unsupported"

            try:
                import redis

                redis_client = redis.Redis.from_url(
                    REDIS_URL, socket_connect_timeout=2, socket_timeout=2
                )
                redis_client.ping()
                checks["redis"] = "ok"
            except Exception:
                checks["redis"] = "error"

            try:
                from app.celery_app import celery_app

                inspector = celery_app.control.inspect(timeout=3)
                if inspector.ping():
                    checks["celery"] = "ok"
                else:
                    checks["celery"] = "unavailable"
            except Exception:
                checks["celery"] = "disabled"

            try:
                backup_dir = Path(current_app.instance_path) / DATA_BACKUP_DIR
                if backup_dir.exists():
                    backups = sorted(
                        backup_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
                    )
                    if backups:
                        age_hours = (time.time() - backups[0].stat().st_mtime) / 3600
                        checks["backup_freshness"] = "ok" if age_hours < 24 else "stale"
                    else:
                        checks["backup_freshness"] = "no_backups"
                else:
                    checks["backup_freshness"] = "no_backups"
            except Exception:
                checks["backup_freshness"] = "error"

            critical_checks = {
                k: v
                for k, v in checks.items()
                if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
            }
            overall = (
                "ok"
                if all(
                    v in ("ok", "running", "disabled", "unsupported")
                    for v in critical_checks.values()
                    if v is not None
                )
                else "degraded"
            )

            result: dict[str, Any] = {
                "status": overall,
                "checks": checks,
                "timestamp": utc_now().isoformat(),
                "details": {
                    "database_latency_ms": round(db_latency_ms, 2),
                    "database_path": str(
                        Path(
                            current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace(
                                "sqlite:///", "/"
                            )
                        )
                        if current_app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith(
                            "sqlite:///"
                        )
                        else "non-sqlite"
                    ),
                    "scheduler_next_run": health.get("next_run"),
                    "scheduler_last_newsletter_send": health.get("last_newsletter_send"),
                },
            }

            return jsonify(result), status_code

        checks = {}
        try:
            db.session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except (OperationalError, ProgrammingError):
            checks["database"] = "error"
            status_code = 503

        health = get_scheduler_health()
        checks["scheduler"] = health["status"]

        return jsonify(
            {
                "status": "ok" if status_code == 200 else "degraded",
                "checks": checks,
                "timestamp": utc_now().isoformat(),
            }
        ), status_code

    @public.route("/metrics")
    @limiter.limit("60 per minute")
    def metrics():
        """Prometheus-compatible metrics endpoint.

        Disabled by default (ENABLE_METRICS=false). When enabled:
        - Production: requires METRICS_SECRET via header or query string
        - Development: allows unauthenticated access when no secret is configured
        """
        if not ENABLE_METRICS:
            return jsonify({"error": "not found"}), 404

        if METRICS_SECRET:
            if not _secret_matches(METRICS_SECRET, "X-Metrics-Secret"):
                return Response("Unauthorized", status=401)
        elif is_production():
            return jsonify({"error": "METRICS_SECRET required in production"}), 403

        if PROMETHEUS_AVAILABLE:
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

        metrics_lines = []

        # Health status
        metrics_lines.append("# HELP blog_health_status Overall health status (1=ok, 0=degraded)")
        metrics_lines.append("# TYPE blog_health_status gauge")
        try:
            db.session.execute(text("SELECT 1"))
            metrics_lines.append("blog_health_status 1")
        except (OperationalError, ProgrammingError):
            metrics_lines.append("blog_health_status 0")

        # Disk free
        metrics_lines.append("# HELP blog_disk_free_bytes Free disk space in bytes")
        metrics_lines.append("# TYPE blog_disk_free_bytes gauge")
        try:
            from app.config.loader import load_effective_config

            metrics_cfg = load_effective_config()
            data_dir_str = metrics_cfg.paths.data_dir if metrics_cfg.paths.data_dir else None
            disk_path = Path(data_dir_str) if data_dir_str else Path.cwd() / "data"
            disk_usage = shutil.disk_usage(disk_path)
            metrics_lines.append(f"blog_disk_free_bytes {disk_usage.free}")
        except OSError:
            metrics_lines.append("blog_disk_free_bytes 0")

        # DB integrity
        metrics_lines.append("# HELP blog_db_integrity Database integrity (1=ok, 0=error)")
        metrics_lines.append("# TYPE blog_db_integrity gauge")
        if is_sqlite_database():
            try:
                result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
                integrity_ok = result and result[0] == "ok"
                metrics_lines.append(f"blog_db_integrity {1 if integrity_ok else 0}")
            except (OperationalError, ProgrammingError):
                metrics_lines.append("blog_db_integrity 0")
        else:
            metrics_lines.append("blog_db_integrity 1")

        # Scheduler status
        metrics_lines.append("# HELP blog_scheduler_status Scheduler status (1=running, 0=stopped)")
        metrics_lines.append("# TYPE blog_scheduler_status gauge")
        try:
            health = get_scheduler_health()
            scheduler_status = 1 if health["status"] == "running" else 0
        except OSError:
            scheduler_status = 0
        metrics_lines.append(f"blog_scheduler_status {scheduler_status}")

        return "\n".join(metrics_lines), 200, {"Content-Type": "text/plain; version=0.0.4"}
