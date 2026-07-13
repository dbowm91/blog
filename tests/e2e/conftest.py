import os
import pytest
from tests.shared_fixtures import *  # noqa: F401, F403
import time

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create application for the test session."""
    db_dir = tmp_path_factory.mktemp("blog_e2e")
    db_path = db_dir / "test.db"

    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    from app import create_app

    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )

    import app.config as _app_config

    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    from app.page_view_buffer import shutdown_page_view_buffer

    shutdown_page_view_buffer()

    from celery import current_app as celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

    yield application


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments."""
    return {
        **browser_type_launch_args,
        "args": ["--no-sandbox", "--disable-setuid-sandbox"],
    }


@pytest.fixture(scope="session")
def app_url():
    """Base URL for the Flask application."""
    return os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5010")


@pytest.fixture(scope="session")
def app_server(app, app_url):
    """Start the Flask server for e2e tests."""
    from app.extensions import db

    with app.app_context():
        db.create_all()
        from app.search import init_fts

        init_fts()

        from app.models import User

        admin = User(username="admin", is_admin=True)
        admin.set_password(os.environ["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()

    app.config["SERVER_NAME"] = "127.0.0.1:5010"

    from threading import Thread

    def run_server():
        from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler

        server = BaseWSGIServer("127.0.0.1", 5010, WSGIRequestHandler)
        server.set_app(app.wsgi_app)
        app._e2e_server = server
        server.serve_forever()

    thread = Thread(target=run_server, daemon=True)
    thread.start()

    import socket

    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", 5010), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)

    yield app_url

    server = getattr(app, "_e2e_server", None)
    if server:
        server.shutdown()
        server.server_close()

    app.config["SERVER_NAME"] = None
