"""Page view buffering for high-traffic sites.

Batches page view writes to reduce database load. Instead of inserting each
page view immediately (synchronous I/O), views are collected in a buffer and
flushed periodically or when a threshold is reached.

Usage:
    Enable via PAGE_VIEW_BUFFER_SIZE env var (default: disabled).
    Set to a number (e.g., "100") to flush when buffer reaches that size.

The buffer is flushed:
1. When it reaches PAGE_VIEW_BUFFER_SIZE (if configured)
2. Every PAGE_VIEW_FLUSH_INTERVAL seconds (default: 5)
3. On application shutdown (graceful flush)
"""

from __future__ import annotations

import os
import threading
import logging
from datetime import datetime, timezone
from queue import Queue, Empty
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from app.config import PAGE_VIEW_BUFFER_SIZE

logger = logging.getLogger(__name__)
PAGE_VIEW_FLUSH_INTERVAL = int(os.environ.get("PAGE_VIEW_FLUSH_INTERVAL", "5"))

_buffer: Optional["PageViewBuffer"] = None
_buffer_lock = threading.Lock()


class PageViewBuffer:
    """Thread-safe buffer for batching page view database inserts.

    Uses a background thread to flush views to the database at intervals,
    reducing database load for high-traffic sites.
    """

    def __init__(
        self, db: Any, PageView: Any, max_size: int = 0, flush_interval: int = 5, app: Any = None
    ) -> None:
        self.db = db
        self.PageView = PageView
        self.max_size = max_size
        self.flush_interval = flush_interval
        self._queue: Queue[tuple[int, Optional[str]]] = Queue()
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False
        self._flush_lock = threading.Lock()
        self._stats = {"flushed": 0, "dropped": 0}
        self._app = app

    def start(self) -> None:
        """Start the background flush thread."""
        if self._started:
            return
        self._stop_event.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        self._started = True
        logger.info(
            "PageViewBuffer started (max_size=%s, flush_interval=%ds)",
            self.max_size or "unlimited",
            self.flush_interval,
        )

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the flush thread and flush remaining views."""
        if not self._started:
            return
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=timeout)
            self._started = False
        self._flush_now()
        logger.info(
            "PageViewBuffer stopped (flushed=%d, dropped=%d)",
            self._stats["flushed"],
            self._stats["dropped"],
        )

    def record(self, post_id: int, referrer: Optional[str] = None) -> None:
        """Record a page view (adds to buffer).

        Args:
            post_id: The ID of the post being viewed
            referrer: Optional referrer URL (sanitized, max 512 chars)
        """
        self._queue.put((post_id, referrer))
        if self.max_size > 0 and self._queue.qsize() >= self.max_size:
            self._flush_now()

    def _flush_loop(self) -> None:
        """Background loop that flushes the buffer periodically."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.flush_interval)
            if not self._stop_event.is_set():
                self._flush_now()

    def _flush_now(self) -> None:
        """Flush all buffered views to the database."""
        with self._flush_lock:
            views = []
            try:
                while True:
                    views.append(self._queue.get_nowait())
            except Empty:
                pass

            if not views:
                return

            ctx = self._app.app_context() if self._app else None
            if ctx:
                ctx.push()
            try:
                self.db.session.execute(
                    self.PageView.__table__.insert(),
                    [
                        {
                            "post_id": post_id,
                            "referrer": referrer,
                            "created_at": datetime.now(timezone.utc),
                        }
                        for post_id, referrer in views
                    ],
                )
                self.db.session.commit()
                self._stats["flushed"] += len(views)
                logger.debug("Flushed %d page views to database", len(views))
            except (SQLAlchemyError, OSError) as e:
                self.db.session.rollback()
                self._stats["dropped"] += len(views)
                logger.error("Failed to flush page views: %s. Dropped %d views", e, len(views))
            finally:
                if ctx:
                    ctx.pop()

    def flush(self) -> int:
        """Manually trigger a flush. Returns number of views flushed."""
        before = self._stats["flushed"]
        self._flush_now()
        return self._stats["flushed"] - before

    @property
    def pending(self) -> int:
        """Return the number of pending views in the buffer."""
        return self._queue.qsize()


def get_buffer() -> Optional["PageViewBuffer"]:
    """Get the global page view buffer instance."""
    global _buffer
    if _buffer is not None:
        return _buffer
    return None


def init_page_view_buffer(db: Any, PageView: Any) -> Optional["PageViewBuffer"]:
    """Initialize the page view buffer if enabled.

    Returns the buffer if PAGE_VIEW_BUFFER_SIZE > 0, otherwise None.
    """
    global _buffer, _buffer_lock

    if PAGE_VIEW_BUFFER_SIZE <= 0:
        return None

    from flask import current_app

    with _buffer_lock:
        if _buffer is None:
            app = current_app._get_current_object()  # type: ignore[attr-defined]
            _buffer = PageViewBuffer(
                db,
                PageView,
                max_size=PAGE_VIEW_BUFFER_SIZE,
                flush_interval=PAGE_VIEW_FLUSH_INTERVAL,
                app=app,
            )
            _buffer.start()

        return _buffer


def record_page_view(post_id: int, referrer: Optional[str] = None) -> None:
    """Record a page view, either buffered or immediate based on config."""
    buffer = get_buffer()
    if buffer is not None:
        buffer.record(post_id, referrer)
    else:
        from app.extensions import db
        from app.models import PageView
        from sqlalchemy.exc import SQLAlchemyError

        try:
            pv = PageView(post_id=post_id, referrer=referrer)
            db.session.add(pv)
            db.session.commit()
            logger.info("PageView recorded directly: post_id=%s", post_id)
        except (SQLAlchemyError, OSError) as e:
            db.session.rollback()
            logger.error("Failed to record PageView directly: %s", e)


def shutdown_page_view_buffer() -> None:
    """Shutdown the page view buffer gracefully."""
    global _buffer
    if _buffer is not None:
        _buffer.stop()
        _buffer = None
