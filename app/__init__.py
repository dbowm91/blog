import os
import logging
from logging.handlers import RotatingFileHandler
import markdown
from flask import Flask
from app.extensions import db, login_manager, migrate
from app.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
from app.csrf import generate_csrf_token, validate_csrf_token

if not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_PASSWORD is required. Set it via the ADMIN_PASSWORD environment variable."
    )


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler - rotates at 10MB, keeps 10 backups
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

    @app.template_filter("markdown")
    def markdown_filter(text):
        return markdown.markdown(text, extensions=["fenced_code", "tables"])

    @app.template_filter("reading_time")
    def reading_time_filter(text):
        if not text:
            return "1 min read"
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"

    @app.before_request
    def check_csrf():
        from flask import request as req
        if req.method == "POST":
            endpoint = req.endpoint or ""
            view_func = app.view_functions.get(endpoint)
            if view_func and getattr(view_func, "_csrf_exempt", False):
                return
            validate_csrf_token()

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "frame-ancestors 'none'"
        )
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

        db.create_all()
        if not User.query.first():
            user = User(username=ADMIN_USERNAME)
            user.set_password(ADMIN_PASSWORD)
            db.session.add(user)
            db.session.commit()

    configure_logging(app)

    from app.scheduler import init_scheduler
    init_scheduler(app)

    return app
