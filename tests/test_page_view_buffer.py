import pytest
from app.page_view_buffer import (
    PageViewBuffer,
    init_page_view_buffer,
    record_page_view,
    shutdown_page_view_buffer,
    get_buffer,
)
from app.models import PageView
from unittest.mock import patch, MagicMock
import os


@pytest.fixture(autouse=True)
def cleanup_buffer():
    """Stop buffer after each test."""
    yield
    shutdown_page_view_buffer()


def test_init_page_view_buffer_disabled(db):
    """Test buffer not initialized when PAGE_VIEW_BUFFER_SIZE <=0."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 0):
        buffer = init_page_view_buffer(db, PageView)
        assert buffer is None
        assert get_buffer() is None


def test_init_page_view_buffer_enabled(db):
    """Test buffer initialized when PAGE_VIEW_BUFFER_SIZE >0."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 10):
        buffer = init_page_view_buffer(db, PageView)
        assert buffer is not None
        assert get_buffer() is buffer
        shutdown_page_view_buffer()
        # Verify buffer is stopped
        assert get_buffer() is None


def test_record_page_view_unbuffered(db):
    """Test record_page_view works without buffer."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 0):
        # Ensure no buffer
        shutdown_page_view_buffer()
        record_page_view(1, "http://example.com")
        # Check PageView was created directly
        pv = db.session.execute(
            db.select(PageView).filter_by(post_id=1)
        ).scalar_one_or_none()
        assert pv is not None
        assert pv.referrer == "http://example.com"


def test_record_page_view_buffered(db):
    """Test record_page_view uses buffer when enabled."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 5):
        buffer = init_page_view_buffer(db, PageView)
        assert buffer is not None
        # Record a view
        record_page_view(1, "http://example.com")
        # View should be in buffer, not yet in DB
        assert buffer.pending == 1
        pv = db.session.execute(
            db.select(PageView).filter_by(post_id=1)
        ).scalar_one_or_none()
        assert pv is None
        # Flush buffer
        flushed = buffer.flush()
        assert flushed == 1
        # Now should be in DB
        pv = db.session.execute(
            db.select(PageView).filter_by(post_id=1)
        ).scalar_one_or_none()
        assert pv is not None
        shutdown_page_view_buffer()


def test_page_view_buffer_flush_on_size(db):
    """Test buffer flushes when max size reached."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 3):
        buffer = init_page_view_buffer(db, PageView)
        # Record 3 views (should trigger flush)
        for i in range(3):
            buffer.record(i+1)
        # Buffer should be empty after flush
        assert buffer.pending == 0
        # Check all 3 views in DB
        pvs = db.session.execute(
            db.select(PageView).filter(PageView.post_id.in_([1,2,3]))
        ).scalars().all()
        assert len(pvs) == 3
        shutdown_page_view_buffer()


def test_shutdown_page_view_buffer(db):
    """Test shutdown flushes remaining views."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 10):
        buffer = init_page_view_buffer(db, PageView)
        buffer.record(1)
        buffer.record(2)
        shutdown_page_view_buffer()
        # Views should be flushed on shutdown
        pvs = db.session.execute(
            db.select(PageView).filter(PageView.post_id.in_([1,2]))
        ).scalars().all()
        assert len(pvs) == 2
        assert get_buffer() is None


def test_page_view_buffer_stats(db):
    """Test buffer stats tracking."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 10):
        buffer = init_page_view_buffer(db, PageView)
        buffer.record(1)
        buffer.flush()
        assert buffer._stats["flushed"] == 1
        shutdown_page_view_buffer()


def test_page_view_buffer_concurrent_access(db):
    """Test buffer handles concurrent access safely."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 100):
        buffer = init_page_view_buffer(db, PageView)
        import threading
        results = []

        def record_views(start, count):
            for i in range(count):
                buffer.record(start + i)
            results.append(count)

        threads = [threading.Thread(target=record_views, args=(i * 10, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sum(results) == 50
        shutdown_page_view_buffer()


def test_page_view_buffer_graceful_shutdown(db):
    """Test buffer flushes all pending views on shutdown."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 100):
        buffer = init_page_view_buffer(db, PageView)
        for i in range(20):
            buffer.record(i + 1)
        initial_pending = buffer.pending
        assert initial_pending == 20
        shutdown_page_view_buffer()
        pvs = db.session.execute(
            db.select(PageView).filter(PageView.post_id.in_(range(1, 21)))
        ).scalars().all()
        assert len(pvs) == 20


def test_record_page_view_no_buffer(app, db):
    """Test record_page_view creates PageView directly when buffer disabled."""
    with patch("app.page_view_buffer.PAGE_VIEW_BUFFER_SIZE", 0):
        shutdown_page_view_buffer()
        from app.page_view_buffer import record_page_view
        record_page_view(99, "http://test.com")
        pv = db.session.execute(
            db.select(PageView).filter_by(post_id=99)
        ).scalar_one_or_none()
        assert pv is not None
        assert pv.referrer == "http://test.com"
