import os
import time
import json
from typing import Any
from urllib.parse import urlparse
import sqlite3
import secrets
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request as req,
    flash,
    session,
    g,
    send_from_directory,
    Response,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_compress import Compress
from flask_caching import Cache
from flask_login import current_user, logout_user
from sqlalchemy import event, text, delete
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db, login_manager, migrate
from app.config import (
    SECRET_KEY,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    SESSION_LIFETIME_HOURS,
    MAX_UPLOAD_SIZE,
)
from app.csrf import validate_csrf_token

# Register sqlite3 datetime adapters for Python 3.12+ compatibility
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("datetime", lambda s: datetime.fromisoformat(s.decode()))


def get_client_ip() -> str:
    forwarded_for = req.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return req.remote_addr or "unknown"


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100 per minute"],
)
compress = Compress()
cache = Cache()

PROMETHEUS_REQUEST_LATENCY = None
PROMETHEUS_REQUEST_COUNT = None
try:
    from prometheus_client import Counter, Histogram

    PROMETHEUS_REQUEST_LATENCY = Histogram(
        "blog_request_latency_seconds",
        "Request latency in seconds",
        ["method", "endpoint", "status"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    PROMETHEUS_REQUEST_COUNT = Counter(
        "blog_requests_total", "Total request count", ["method", "endpoint", "status"]
    )
except ImportError:
    pass

logger = logging.getLogger(__name__)


class StructuredLogFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "request_id",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
            ):
                if value is not None:
                    log_data[key] = value
        return json.dumps(log_data)


def configure_logging(app: Flask) -> None:
    """Configure application logging with request context."""

    class RequestIdFilter(logging.Filter):
        """Inject request_id into log records."""

        def filter(self, record: logging.LogRecord) -> bool:
            try:
                record.request_id = getattr(g, "request_id", "-")
            except RuntimeError:
                record.request_id = "-"
            return True

    if not app.debug and not app.testing:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "blog.log"), maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(StructuredLogFormatter())
        file_handler.addFilter(RequestIdFilter())
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Blog startup")


def create_app() -> Flask:
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is required. Set it via the SECRET_KEY environment variable."
        )
    if len(SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 characters long for security. "
            "Current length: {}.".format(len(SECRET_KEY))
        )
    if not ADMIN_PASSWORD:
        raise RuntimeError(
            "ADMIN_PASSWORD is required. Set it via the ADMIN_PASSWORD environment variable."
        )
    from app.config import _validate_config, _config as _raw_config  # noqa: E402

    _validate_config(_raw_config)

    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    if "SQLALCHEMY_DATABASE_URI" in os.environ:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]
    else:
        db_path = os.path.join(app.instance_path, "blog.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE + 1024 * 1024
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
        "SESSION_COOKIE_SECURE", "true"
    ).lower() in ("true", "1", "yes")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    proxy_count = int(os.environ.get("PROXY_COUNT", 1))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=1, x_host=1)  # type: ignore[method-assign]

    if not app.debug and not app.testing:
        csrf_disabled = not app.config.get("CSRF_ENABLED", True)
        if csrf_disabled:
            logger.warning(
                "CSRF protection is disabled in production mode. "
                "This is a security risk. Set CSRF_ENABLED=True in production."
            )
        if not app.config.get("SESSION_COOKIE_SECURE", True):
            raise RuntimeError(
                "SESSION_COOKIE_SECURE must be True in production. This is a security requirement."
            )

    db.init_app(app)

    if not app.debug and not app.testing:
        # Only apply connection pool settings for non-SQLite databases
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        parsed_uri = urlparse(db_uri)
        if parsed_uri.scheme != "sqlite":
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "pool_timeout": 30,
            }

    from app.config import RATE_LIMIT_STORAGE_URI  # noqa: E402

    app.config["RATELIMIT_STORAGE_URI"] = RATE_LIMIT_STORAGE_URI
    app.config["RATELIMIT_HEADERS_ENABLED"] = False

    limiter.init_app(app)
    if os.environ.get("FLASK_ENV") == "production":
        cache_config = {
            "CACHE_TYPE": "RedisCache",
            "CACHE_REDIS_URL": os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0"),
            "CACHE_DEFAULT_TIMEOUT": 300,
            "CACHE_KEY_PREFIX": "blog_",
        }
    else:
        cache_config = {
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": 300,
        }
    cache.init_app(app, config=cache_config)
    compress.init_app(app)

    if os.environ.get("TESTING") or app.config.get("TESTING"):
        limiter.enabled = False

    @app.errorhandler(429)
    def ratelimit_handler(e: Any) -> tuple[Any, int]:
        if req.is_json:
            from flask import jsonify  # noqa: E402

            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        return render_template("429.html", error=str(e.description)), 429

    with app.app_context():

        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.routes.public import public  # noqa: E402
    from app.routes.admin import admin  # noqa: E402
    from app.routes.admin import posts  # noqa: F401 # Triggers route registration via posts/__init__.py
    from app.routes.rss import rss  # noqa: E402
    from app.routes.errors import errors  # noqa: E402
    from app.routes.api import api  # noqa: E402

    app.register_blueprint(public)
    app.register_blueprint(admin)
    app.register_blueprint(rss)
    app.register_blueprint(errors)
    app.register_blueprint(api)

    from flask_swagger_ui import get_swaggerui_blueprint  # noqa: E402

    SWAGGER_URL = "/api/docs"
    API_URL = "/openapi.yaml"
    swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    @app.route("/openapi.yaml")
    def openapi_spec():
        return send_from_directory(app.root_path, "../docs/openapi.yaml")

    from app.filters import register_filters  # noqa: E402

    register_filters(app)

    SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_HOURS * 3600

    @app.before_request
    def before_request_handler() -> Response | None:
        # Generate request ID and CSP nonce for this request
        g.request_id = secrets.token_hex(4)
        g.csp_nonce = secrets.token_urlsafe(16)
        g.request_start_time = time.perf_counter()

        # CSRF validation for POST requests
        if req.method == "POST":
            validate_csrf_token()

        # Session timeout check for authenticated users
        # Uses custom sliding expiration based on last_activity stored in session.
        # Each request updates last_activity if within SESSION_LIFETIME_SECONDS.
        # If more than SESSION_LIFETIME_SECONDS pass without activity, user is logged out.
        if current_user.is_authenticated:
            last_activity = session.get("last_activity")
            now = time.time()
            if last_activity:
                try:
                    last = float(last_activity)
                except (ValueError, TypeError):
                    last = 0.0  # Legacy format or corrupted; treat as expired
                if (now - last) > SESSION_LIFETIME_SECONDS:
                    # Clean up admin session tracking
                    sid = session.pop("admin_session_id", None)
                    if sid:
                        from app.models import AdminSession  # noqa: E402
                        from sqlalchemy.exc import IntegrityError, OperationalError  # noqa: E402

                        try:
                            db.session.execute(
                                delete(AdminSession).where(AdminSession.session_id == sid)
                            )
                            db.session.commit()
                        except (IntegrityError, OperationalError):
                            db.session.rollback()
                            logger.warning("Failed to delete expired admin session: %s", sid)
                    logout_user()
                    flash("Session expired. Please log in again.", "info")
                    return redirect(url_for("admin.login"))
            session["last_activity"] = now
        return None

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        from flask import current_app  # noqa: E402

        nonce = getattr(g, "csp_nonce", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not current_app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"style-src-attr 'unsafe-inline'; "
            f"font-src 'self'; "
            f"img-src 'self' data:; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"connect-src 'self'; "
            f"frame-src 'none'; "
            f"frame-ancestors 'none'"
        )
        if current_app.debug:
            response.headers["Content-Security-Policy-Report-Only"] = (
                f"default-src 'self'; "
                f"style-src 'self' 'nonce-{nonce}'; "
                f"style-src-attr 'unsafe-inline'; "
                f"font-src 'self'; "
                f"img-src 'self' data:; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"connect-src 'self' report-uri /csp-violation; "
                f"frame-src 'none'; "
                f"frame-ancestors 'none'"
            )
        if req.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        if PROMETHEUS_REQUEST_LATENCY and PROMETHEUS_REQUEST_COUNT:
            start_time = getattr(g, "request_start_time", None)
            if start_time is not None:
                latency = time.perf_counter() - start_time
                status_code = str(response.status_code)
                endpoint = req.endpoint or "unknown"
                PROMETHEUS_REQUEST_LATENCY.labels(
                    method=req.method, endpoint=endpoint, status=status_code
                ).observe(latency)
                PROMETHEUS_REQUEST_COUNT.labels(
                    method=req.method, endpoint=endpoint, status=status_code
                ).inc()

        return response

    from app.context_processors import register_context_processors  # noqa: E402

    register_context_processors(app)

    with app.app_context():
        from app.models import User  # noqa: E402
        from app.search import init_fts  # noqa: E402
        from sqlalchemy.exc import IntegrityError, OperationalError  # noqa: E402

        try:
            existing_user = db.session.execute(
                db.select(User).order_by(User.id).limit(1)
            ).scalar_one_or_none()
            if not existing_user:
                user = User(username=ADMIN_USERNAME, is_admin=True)
                user.set_password(ADMIN_PASSWORD)
                db.session.add(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
            elif not existing_user.is_admin:
                # Promote first user to admin if not already
                existing_user.is_admin = True
                db.session.commit()
        except OperationalError:
            db.session.rollback()

        # Initialize SiteSettings if none exist
        try:
            from app.models import SiteSettings  # noqa: E402

            existing_settings = db.session.execute(
                db.select(SiteSettings).order_by(SiteSettings.id).limit(1)
            ).scalar_one_or_none()
            if not existing_settings:
                settings = SiteSettings()
                db.session.add(settings)
                db.session.commit()
        except OperationalError:
            db.session.rollback()

        try:
            init_fts()
        except OperationalError:
            db.session.rollback()

    configure_logging(app)

    def _check_database_integrity(app: Flask) -> None:
        """Run PRAGMA integrity_check to verify database is not corrupted."""
        with app.app_context():
            try:
                result = db.session.execute(text("PRAGMA integrity_check"))
                row = result.scalar()
                if row != "ok":
                    logger.warning(
                        "Database integrity check failed: %s. Consider restoring from backup.",
                        row,
                    )
                else:
                    logger.info("Database integrity check passed")
            except SQLAlchemyError as e:
                logger.warning("Database integrity check failed: %s", e)

    _check_database_integrity(app)

    from app.scheduler import init_scheduler  # noqa: E402

    init_scheduler(app)

    from app.page_view_buffer import init_page_view_buffer  # noqa: E402
    from app.models import PageView  # noqa: E402

    init_page_view_buffer(db, PageView)

    from app.cli import register_cli_commands  # noqa: E402

    register_cli_commands(app)

    from app.vite import init_vite  # noqa: E402

    init_vite(app)

    @app.shell_context_processor
    def make_shell_context() -> dict[str, Any]:
        from app.models import (  # noqa: E402
            User,
            Post,
            Tag,
            Subscriber,
            Page,
            PageView,
            ShareEvent,
            AdminSession,
            SiteSettings,
        )

        return {
            "db": db,
            "User": User,
            "Post": Post,
            "Tag": Tag,
            "Subscriber": Subscriber,
            "Page": Page,
            "PageView": PageView,
            "ShareEvent": ShareEvent,
            "AdminSession": AdminSession,
            "SiteSettings": SiteSettings,
        }

    return app
