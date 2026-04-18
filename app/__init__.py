import os
import time
import secrets
import logging
from logging.handlers import RotatingFileHandler
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request as req,
    flash,
    session,
    g,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import current_user, logout_user
from sqlalchemy import event
from app.extensions import db, login_manager, migrate
from app.config import (
    SECRET_KEY,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    SESSION_LIFETIME_HOURS,
    MAX_UPLOAD_SIZE,
)
from app.csrf import generate_csrf_token, validate_csrf_token
from sqlalchemy import select, text

logger = logging.getLogger(__name__)


def configure_logging(app):
    """Configure application logging with request context."""

    class RequestIdFilter(logging.Filter):
        """Inject request_id into log records."""

        def filter(self, record):
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
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(request_id)s] %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.addFilter(RequestIdFilter())
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Blog startup")


def create_app():
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
    from app.config import _validate_config, _config as _raw_config

    _validate_config(_raw_config)

    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(__file__), "static", "uploads"
    )
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
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=1, x_host=1)

    if not app.debug and not app.testing:
        csrf_disabled = not app.config.get("CSRF_ENABLED", True)
        if csrf_disabled:
            logger.warning(
                "CSRF protection is disabled in production mode. "
                "This is a security risk. Set CSRF_ENABLED=True in production."
            )

    db.init_app(app)

    with app.app_context():

        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.routes.public import public
    from app.routes.admin import admin
    from app.routes.rss import rss
    from app.routes.errors import errors

    app.register_blueprint(public)
    app.register_blueprint(admin)
    app.register_blueprint(rss)
    app.register_blueprint(errors)

    import nh3
    import markdown
    from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES

    @app.template_filter("markdown_safe")
    def markdown_safe_filter(text: str) -> str:
        html = markdown.markdown(text, extensions=["fenced_code", "tables"])
        return nh3.clean(
            html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
        )

    @app.template_filter("reading_time")
    def reading_time_filter(text: str) -> str:
        if not text:
            return "1 min read"
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"

    @app.template_filter("sanitize_css")
    def sanitize_css_filter(text):
        from app.utils import sanitize_css

        return sanitize_css(text) if text else ""

    @app.template_filter("post_image_url")
    def post_image_url_filter(post):
        if not post or not post.image:
            return None
        path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
        if os.path.isfile(path):
            return post.image
        return None

    SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_HOURS * 3600

    @app.before_request
    def before_request_handler():
        from app.utils import utc_now

        # Generate request ID and CSP nonce for this request
        g.request_id = secrets.token_hex(4)
        g.csp_nonce = secrets.token_urlsafe(16)

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
                        from app.models import AdminSession

                        admin_session = db.session.execute(
                            select(AdminSession).filter_by(session_id=sid)
                        ).scalar_one_or_none()
                        if admin_session:
                            from sqlalchemy.exc import IntegrityError, OperationalError

                            try:
                                db.session.delete(admin_session)
                                db.session.commit()
                            except (IntegrityError, OperationalError):
                                db.session.rollback()
                                logger.warning(
                                    "Failed to delete expired admin session: %s", sid
                                )
                    logout_user()
                    flash("Session expired. Please log in again.", "info")
                    return redirect(url_for("admin.login"))
            session["last_activity"] = now

    @app.after_request
    def set_security_headers(response):
        from flask import current_app

        nonce = getattr(g, "csp_nonce", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if not current_app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
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
        return response

    from app.context_processors import register_context_processors

    register_context_processors(app)

    with app.app_context():
        from app.models import User
        from app.search import init_fts
        from sqlalchemy.exc import IntegrityError, OperationalError

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
            from app.models import SiteSettings

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

    def _check_database_integrity(app):
        """Run PRAGMA integrity_check to verify database is not corrupted."""
        with app.app_context():
            try:
                result = db.session.execute(text("PRAGMA integrity_check"))
                row = result.scalar()
                if row != "ok":
                    logger.warning(
                        "Database integrity check failed: %s. "
                        "Consider restoring from backup.",
                        row,
                    )
                else:
                    logger.info("Database integrity check passed")
            except Exception as e:
                logger.warning("Database integrity check failed: %s", e)

    _check_database_integrity(app)

    from app.scheduler import init_scheduler

    init_scheduler(app)

    from app.cli import register_cli_commands

    register_cli_commands(app)

    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
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
