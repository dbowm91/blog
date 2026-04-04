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
    db_path = os.path.join(app.instance_path, "blog.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE + 1024 * 1024
    app.config["SESSION_COOKIE_SECURE"] = not app.debug
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    proxy_count = int(os.environ.get("PROXY_COUNT", 1))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=1, x_host=1)

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

    app.register_blueprint(public)
    app.register_blueprint(admin)
    app.register_blueprint(rss)

    @app.errorhandler(404)
    def not_found(e):
        from app.models import Post

        try:
            recent_posts = (
                db.session.execute(
                    select(Post)
                    .filter_by(published=True)
                    .order_by(Post.created_at.desc())
                    .limit(5)
                )
                .scalars()
                .all()
            )
        except Exception:
            recent_posts = []
        return render_template(
            "404.html",
            recent_posts=recent_posts,
            error_code="404",
            error_title="Page not found",
            error_message="The page you're looking for doesn't exist or has been moved.",
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        from app.models import Post

        db.session.rollback()
        app.logger.exception("Unhandled exception on %s", req.path)
        try:
            recent_posts = (
                db.session.execute(
                    select(Post)
                    .filter_by(published=True)
                    .order_by(Post.created_at.desc())
                    .limit(5)
                )
                .scalars()
                .all()
            )
        except Exception:
            recent_posts = []
        return render_template(
            "500.html",
            recent_posts=recent_posts,
            error_code="500",
            error_title="Internal Server Error",
            error_message="Something went wrong. Please try again later.",
        ), 500

    @app.errorhandler(413)
    def handle_large_request(e):
        flash(
            f"File too large. Maximum upload size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            "error",
        )
        return redirect(req.referrer or url_for("admin.dashboard"))

    import nh3
    import markdown
    from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES

    @app.template_filter("markdown_safe")
    def markdown_safe_filter(text):
        html = markdown.markdown(text, extensions=["fenced_code", "tables"])
        return nh3.clean(
            html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
        )

    @app.template_filter("reading_time")
    def reading_time_filter(text):
        if not text:
            return "1 min read"
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"

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

    @app.context_processor
    def inject_csrf():
        nonce = getattr(g, "csp_nonce", "")
        return {"csrf_token": generate_csrf_token(), "csp_nonce": nonce}

    @app.context_processor
    def inject_config():
        from datetime import datetime
        from app.config import (
            APP_TITLE,
            APP_DESCRIPTION,
            AUTHOR_NAME,
            AUTHOR_ROLE,
            AUTHOR_AVATAR,
            BASE_URL,
        )

        return {
            "site_title": APP_TITLE,
            "site_description": APP_DESCRIPTION,
            "author_name": AUTHOR_NAME,
            "author_role": AUTHOR_ROLE,
            "author_avatar": AUTHOR_AVATAR,
            "base_url": BASE_URL,
            "current_year": datetime.now().year,
        }

    @app.context_processor
    def inject_footer_data():
        from datetime import datetime
        from app.models import Post, Tag
        from app.cache import _get_tag_counts

        try:
            recent_posts = (
                db.session.execute(
                    select(Post)
                    .filter_by(published=True)
                    .order_by(Post.created_at.desc())
                    .limit(3)
                )
                .scalars()
                .all()
            )
            footer_tags = (
                db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
            )
            tag_counts = _get_tag_counts()
            return {
                "recent_posts_footer": recent_posts,
                "footer_tags": footer_tags,
                "footer_tag_counts": tag_counts,
            }
        except Exception:
            return {
                "recent_posts_footer": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

    @app.context_processor
    def inject_show_footer_posts():
        from flask import request

        path = request.path
        return {
            "show_footer_posts": not (
                path.startswith("/search") or path.startswith("/tag/")
            )
        }

    with app.app_context():
        from app.models import User
        from app.search import init_fts
        from sqlalchemy.exc import IntegrityError, OperationalError

        try:
            existing_user = db.session.execute(
                db.select(User).order_by(User.id)
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

        try:
            init_fts()
        except OperationalError:
            db.session.rollback()

    configure_logging(app)

    from app.scheduler import init_scheduler

    init_scheduler(app)

    import click

    @app.cli.command("rebuild-search")
    def rebuild_search_command():
        """Rebuild the FTS5 search index."""
        from app.search import rebuild_fts

        rebuild_fts()
        click.echo("Search index rebuilt.")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create a new admin user or promote an existing user."""
        import click

        username = click.prompt("Username")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

        from app.models import User
        from app.routes.admin.helpers import _check_password_complexity

        if not _check_password_complexity(password):
            click.echo(
                "Password must be at least 8 characters and contain at least 3 of 4: "
                "lowercase, uppercase, digit, special."
            )
            return

        existing = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if existing:
            existing.is_admin = True
            existing.set_password(password)
            db.session.commit()
            click.echo(f"User '{username}' promoted to admin.")
        else:
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            click.echo(f"Admin user '{username}' created.")

    return app
