"""Meta routes - robots.txt, sitemap.xml, favicon, health check, metrics."""

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
from app.models import Post, Tag, Page
from app.config import BASE_URL, SMTP_HOST, HEALTH_CHECK_SECRET
from app.scheduler import get_scheduler_health
from app.utils import xml_escape, utc_now
from app import limiter

logger = logging.getLogger(__name__)


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
        db.session.execute(
            select(Page).filter_by(published=True).order_by(Page.updated_at.desc())
        )
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
        db.session.execute(
            select(Post).filter_by(published=True).order_by(Post.updated_at.desc())
        )
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
        """Health check endpoint for monitoring."""
        import hmac

        detailed = request.args.get("detailed", "").lower() == "true"
        secret = request.args.get("secret", "")
        is_detailed = (
            detailed
            and HEALTH_CHECK_SECRET
            and hmac.compare_digest(secret, HEALTH_CHECK_SECRET)
        )

        checks = {}
        status_code = 200

        # Database check with latency
        db_start = time.perf_counter()
        try:
            db.session.execute(text("SELECT 1"))
            db_latency_ms = (time.perf_counter() - db_start) * 1000
            checks["database"] = "ok"
        except (OperationalError, ProgrammingError):
            db_latency_ms = (time.perf_counter() - db_start) * 1000
            checks["database"] = "error"
            status_code = 503

        # Scheduler check
        if SMTP_HOST:
            health = get_scheduler_health()
            checks["scheduler"] = health["status"]
        else:
            checks["scheduler"] = "disabled"

        # FTS check
        try:
            has_fts = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
            ).fetchone()
            checks["search"] = "ok" if has_fts else "unavailable"
        except (OperationalError, ProgrammingError):
            checks["search"] = "error"

        # Disk space check
        try:
            disk_path = Path(current_app.instance_path)
            disk_usage = shutil.disk_usage(disk_path)
            free_percent = (disk_usage.free / disk_usage.total) * 100
            checks["disk_space"] = "ok" if free_percent >= 10 else "low"
        except OSError:
            checks["disk_space"] = "error"

        # Database integrity check
        try:
            integrity_result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
            checks["db_integrity"] = "ok" if integrity_result and integrity_result[0] == "ok" else "error"
        except (OperationalError, ProgrammingError):
            checks["db_integrity"] = "error"

        overall = (
            "ok"
            if all(v in ("ok", "running", "disabled") for v in checks.values() if v is not None)
            else "degraded"
        )

        result: dict[str, Any] = {
            "status": overall,
            "checks": checks,
            "timestamp": utc_now().isoformat(),
        }

        if is_detailed:
            result["details"] = {
                "database_latency_ms": round(db_latency_ms, 2),
            }
            if SMTP_HOST:
                health = get_scheduler_health()
                result["details"]["scheduler_next_run"] = health.get("next_run")
                result["details"]["scheduler_last_newsletter_send"] = health.get(
                    "last_newsletter_send"
                )

        return jsonify(result), status_code

    @public.route("/metrics")
    def metrics():
        """Prometheus-compatible metrics endpoint."""
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
            disk_path = Path(current_app.instance_path)
            disk_usage = shutil.disk_usage(disk_path)
            metrics_lines.append(f"blog_disk_free_bytes {disk_usage.free}")
        except OSError:
            metrics_lines.append("blog_disk_free_bytes 0")

        # DB integrity
        metrics_lines.append("# HELP blog_db_integrity Database integrity (1=ok, 0=error)")
        metrics_lines.append("# TYPE blog_db_integrity gauge")
        try:
            result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
            integrity_ok = result and result[0] == "ok"
            metrics_lines.append(f"blog_db_integrity {1 if integrity_ok else 0}")
        except (OperationalError, ProgrammingError):
            metrics_lines.append("blog_db_integrity 0")

        # Scheduler status
        metrics_lines.append("# HELP blog_scheduler_status Scheduler status (1=running, 0=stopped)")
        metrics_lines.append("# TYPE blog_scheduler_status gauge")
        scheduler_status = 1  # disabled is ok
        if SMTP_HOST:
            try:
                health = get_scheduler_health()
                scheduler_status = 1 if health["status"] == "running" else 0
            except OSError:
                scheduler_status = 0
        metrics_lines.append(f"blog_scheduler_status {scheduler_status}")

        return "\n".join(metrics_lines), 200, {"Content-Type": "text/plain; version=0.0.4"}
