import signal
import threading
from asgiref.wsgi import WsgiToAsgi
from app import create_app
from app.config import SERVER_HOST, SERVER_PORT, DEBUG

app = create_app()
asgi_app = WsgiToAsgi(app)

_shutdown_event = threading.Event()
_scheduler = None


def _get_scheduler():
    global _scheduler
    if _scheduler is None:
        from app.scheduler import init_scheduler

        _scheduler = init_scheduler(app)
    return _scheduler


def _shutdown_handler(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    import logging

    logger = logging.getLogger(__name__)

    if _shutdown_event.is_set():
        logger.warning("Shutdown already in progress, ignoring duplicate SIGTERM")
        return

    _shutdown_event.set()
    logger.info("Graceful shutdown initiated")

    scheduler = _get_scheduler()
    if scheduler is not None:
        logger.info("Stopping scheduler (waiting for current jobs to complete)")
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    from app.page_view_buffer import shutdown_page_view_buffer

    shutdown_page_view_buffer()

    from app.extensions import db

    logger.info("Closing database connections")
    db.engine.dispose()
    logger.info("Database connections closed")


signal.signal(signal.SIGTERM, _shutdown_handler)


if __name__ == "__main__":
    _get_scheduler()
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
