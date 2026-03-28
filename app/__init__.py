import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from app.extensions import db, login_manager, migrate
from app.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_LIFETIME_HOURS
from app.csrf import generate_csrf_token, validate_csrf_token


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'blog.log'),
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Blog startup')


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
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SESSION_COOKIE_SECURE"] = not app.debug
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    db.init_app(app)
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
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template
        db.session.rollback()
        return render_template("500.html"), 500

    @app.errorhandler(413)
    def handle_large_request(e):
        from flask import redirect, url_for, request as req, flash
        flash("File too large. Maximum upload size is 16MB.", "error")
        return redirect(req.referrer or url_for("admin.dashboard"))

    import nh3
    from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES

    @app.template_filter("markdown_safe")
    def markdown_safe_filter(text):
        import markdown
        html = markdown.markdown(text, extensions=["fenced_code", "tables"])
        return nh3.clean(html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES)

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
        from flask import request as req, session, redirect, url_for, flash
        from flask_login import current_user, logout_user
        from datetime import datetime, timezone
        import time
        from app.utils import utc_now

        # CSRF validation for POST requests
        if req.method == "POST":
            endpoint = req.endpoint or ""
            view_func = app.view_functions.get(endpoint)
            if view_func and getattr(view_func, "_csrf_exempt", False):
                pass
            else:
                validate_csrf_token()

        # Session timeout check for authenticated users
        if current_user.is_authenticated:
            last_activity = session.get("last_activity")
            now = time.time()
            if last_activity:
                # Support both old ISO format (UTC naive) and new float timestamp
                if isinstance(last_activity, str):
                    try:
                        last_dt = datetime.fromisoformat(last_activity)
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                        last = last_dt.timestamp()
                    except ValueError:
                        # Malformed, treat as expired
                        last = 0.0
                else:
                    # Assume float timestamp
                    last = float(last_activity)
                if (now - last) > SESSION_LIFETIME_SECONDS:
                    logout_user()
                    flash("Session expired. Please log in again.", "info")
                    return redirect(url_for("admin.login"))
            session["last_activity"] = now

    @app.after_request
    def set_security_headers(response):
        from flask import request as req
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "font-src 'self'; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "frame-ancestors 'none'"
        )
        if req.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": generate_csrf_token()}

    @app.context_processor
    def inject_config():
        from app.config import APP_TITLE, APP_DESCRIPTION, AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_AVATAR, BASE_URL
        return {
            "site_title": APP_TITLE,
            "site_description": APP_DESCRIPTION,
            "author_name": AUTHOR_NAME,
            "author_role": AUTHOR_ROLE,
            "author_avatar": AUTHOR_AVATAR,
            "base_url": BASE_URL,
        }

    with app.app_context():
        from app.models import User
        from sqlalchemy.exc import IntegrityError, OperationalError

        try:
            existing_user = User.query.first()
            if not existing_user:
                user = User(username=ADMIN_USERNAME)
                user.set_password(ADMIN_PASSWORD)
                db.session.add(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
            elif not existing_user.check_password(ADMIN_PASSWORD):
                app.logger.warning(
                    "ADMIN_PASSWORD env var does not match the password hash for user '%s'. "
                    "The stored password has not been changed.",
                    existing_user.username,
                )
        except OperationalError:
            db.session.rollback()

    configure_logging(app)

    from app.scheduler import init_scheduler
    init_scheduler(app)

    return app
