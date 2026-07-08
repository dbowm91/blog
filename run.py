import signal
import threading
from dotenv import load_dotenv

load_dotenv()

from asgiref.wsgi import WsgiToAsgi  # noqa: E402
from app import create_app  # noqa: E402
from app.config import SERVER_HOST, SERVER_PORT, DEBUG  # noqa: E402

app = create_app()
asgi_app = WsgiToAsgi(app)

_shutdown_event = threading.Event()


def _shutdown_handler(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    import logging

    logger = logging.getLogger(__name__)

    if _shutdown_event.is_set():
        logger.warning("Shutdown already in progress, ignoring duplicate SIGTERM")
        return

    _shutdown_event.set()
    logger.info("Graceful shutdown initiated")

    from app.scheduler import shutdown_scheduler, get_scheduler_status

    if get_scheduler_status():
        logger.info("Stopping scheduler (waiting for current jobs to complete)")
        shutdown_scheduler(wait=True)
        logger.info("Scheduler stopped")

    from app.page_view_buffer import shutdown_page_view_buffer

    shutdown_page_view_buffer()

    from app.extensions import db

    logger.info("Closing database connections")
    db.engine.dispose()
    logger.info("Database connections closed")


signal.signal(signal.SIGTERM, _shutdown_handler)


if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
