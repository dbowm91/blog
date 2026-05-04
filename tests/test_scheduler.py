import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timezone
from app.utils import utc_now
from filelock import Timeout as FileLockTimeout


def test_get_scheduler_status_not_running():
    """Test get_scheduler_status when scheduler not running."""
    from app.scheduler import get_scheduler_status
    with patch("app.scheduler._scheduler_running") as mock_event:
        mock_event.is_set.return_value = False
        assert get_scheduler_status() is False


def test_get_scheduler_status_running():
    """Test get_scheduler_status when scheduler is running."""
    from app.scheduler import get_scheduler_status
    with patch("app.scheduler._scheduler_running") as mock_event:
        mock_event.is_set.return_value = True
        assert get_scheduler_status() is True


def test_get_scheduler_next_run_no_scheduler():
    """Test get_scheduler_next_run with no scheduler."""
    from app.scheduler import get_scheduler_next_run
    with patch("app.scheduler._scheduler", None):
        assert get_scheduler_next_run() is None


def test_get_scheduler_health():
    """Test get_scheduler_health returns correct info."""
    from app.scheduler import get_scheduler_health, get_scheduler_next_run
    with patch("app.scheduler._scheduler_running") as mock_running, \
         patch("app.scheduler._last_newsletter_send") as mock_last, \
         patch("app.scheduler.get_scheduler_next_run") as mock_next:
        mock_running.is_set.return_value = True
        mock_last.return_value = utc_now()
        mock_next.return_value = utc_now()
        health = get_scheduler_health()
        assert health["status"] == "running"
        assert health["last_newsletter_send"] is not None
        assert health["next_run"] is not None


def test_send_daily_newsletter_no_posts(db):
    """Test send_daily_newsletter with no posts to send."""
    from app.scheduler import send_daily_newsletter
    from app.models import Post
    from filelock import Timeout as FileLockTimeout
    from unittest.mock import patch as mock_patch
    app = MagicMock()
    with mock_patch("app.scheduler.FileLock") as mock_lock:
        # Create a valid FileLockTimeout instance
        timeout_exception = FileLockTimeout("/tmp/test.lock")
        mock_lock.return_value.acquire.side_effect = timeout_exception
        # Should return early
        send_daily_newsletter(app)
        # No posts should be updated
        posts = db.session.execute(db.select(Post)).scalars().all()
        for post in posts:
            assert post.newsletter_sent_at is None


def test_cleanup_expired_subscribers(db):
    """Test cleanup_expired_subscribers removes expired unconfirmed subs."""
    from app.scheduler import cleanup_expired_subscribers
    from app.models import Subscriber
    # Create expired subscriber
    sub = Subscriber(
        email="expired@example.com",
        confirmed=False,
        expires_at=utc_now().replace(year=2020)
    )
    db.session.add(sub)
    db.session.commit()
    app = MagicMock()
    with patch("app.scheduler.FileLock") as mock_lock:
        mock_lock.return_value.acquire.return_value = True
        cleanup_expired_subscribers(app)
        # Subscriber should be deleted
        deleted = db.session.execute(
            db.select(Subscriber).filter_by(email="expired@example.com")
        ).scalar_one_or_none()
        assert deleted is None


def test_publish_scheduled_posts(db, sample_post):
    """Test publish_scheduled_posts publishes due posts."""
    from app.scheduler import publish_scheduled_posts
    from app.models import Post
    # Set post to be scheduled in the past
    sample_post.published = False
    sample_post.scheduled_publish_at = utc_now().replace(year=2020)
    db.session.commit()
    app = MagicMock()
    with patch("app.scheduler.FileLock") as mock_lock:
        mock_lock.return_value.acquire.return_value = True
        publish_scheduled_posts(app)
        db.session.expire(sample_post)
        sample_post = db.session.get(Post, sample_post.id)
        assert sample_post.published is True
        assert sample_post.scheduled_publish_at is None


def test_init_scheduler_no_smtp():
    """Test init_scheduler returns None if SMTP_HOST not set."""
    from app.scheduler import init_scheduler
    from app.config import SMTP_HOST
    with patch("app.config.SMTP_HOST", None):
        app = MagicMock()
        app.instance_path = "/tmp"
        result = init_scheduler(app)
        assert result is None


def test_init_scheduler_with_smtp():
    """Test init_scheduler initializes when SMTP_HOST is set."""
    from app.scheduler import init_scheduler
    # Patch the BackgroundScheduler where it's imported in scheduler module
    with patch("apscheduler.schedulers.background.BackgroundScheduler") as MockScheduler:
        mock_scheduler = MagicMock()
        MockScheduler.return_value = mock_scheduler
        with patch("app.config.SMTP_HOST", "smtp.example.com"), \
             patch("app.config.NEWSLETTER_SEND_TIME", "09:00"):
            app = MagicMock()
            app.instance_path = "/tmp"
            result = init_scheduler(app)
            assert result is not None
            assert mock_scheduler.start.called
            assert mock_scheduler.add_job.called
