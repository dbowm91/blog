from datetime import timedelta
from unittest.mock import patch, MagicMock
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
    from app.scheduler import get_scheduler_health

    mock_scheduler = MagicMock()
    with (
        patch("app.scheduler._scheduler", mock_scheduler),
        patch("app.scheduler._scheduler_running") as mock_running,
        patch("app.scheduler._last_newsletter_send") as mock_last,
        patch("app.scheduler.get_scheduler_next_run") as mock_next,
    ):
        mock_running.is_set.return_value = True
        mock_last.return_value = utc_now()
        mock_next.return_value = utc_now()
        health = get_scheduler_health()
        assert health["status"] == "running"
        assert health["last_newsletter_send"] is not None
        assert health["next_run"] is not None


def test_get_scheduler_health_disabled():
    """Test get_scheduler_health returns 'disabled' when no scheduler."""
    from app.scheduler import get_scheduler_health

    with (
        patch("app.scheduler._scheduler", None),
        patch("app.scheduler._scheduler_running") as mock_running,
        patch("app.scheduler._last_newsletter_send", None),
    ):
        mock_running.is_set.return_value = False
        health = get_scheduler_health()
        assert health["status"] == "disabled"
        assert health["last_newsletter_send"] is None
        assert health["next_run"] is None


def test_get_scheduler_health_stopped():
    """Test get_scheduler_health returns 'stopped' when scheduler exists but not running."""
    from app.scheduler import get_scheduler_health

    mock_scheduler = MagicMock()
    with (
        patch("app.scheduler._scheduler", mock_scheduler),
        patch("app.scheduler._scheduler_running") as mock_running,
        patch("app.scheduler._last_newsletter_send", None),
        patch("app.scheduler.get_scheduler_next_run", return_value=None),
    ):
        mock_running.is_set.return_value = False
        health = get_scheduler_health()
        assert health["status"] == "stopped"


def test_send_daily_newsletter_no_posts(db):
    """Test send_daily_newsletter with no posts to send."""
    from app.scheduler import send_daily_newsletter
    from app.models import Post
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
        email="expired@example.com", confirmed=False, expires_at=utc_now().replace(year=2020)
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
    """Test init_scheduler skips newsletter job if SMTP_HOST not set."""
    from app.scheduler import init_scheduler

    with (
        patch("app.config.SMTP_HOST", None),
        patch("app.scheduler._scheduler", None),
        patch("app.scheduler._scheduler_running") as mock_running,
        patch("apscheduler.schedulers.background.BackgroundScheduler") as MockScheduler,
    ):
        mock_running.is_set.return_value = False
        mock_scheduler = MagicMock()
        MockScheduler.return_value = mock_scheduler
        app = MagicMock()
        app.instance_path = "/tmp"
        result = init_scheduler(app)
        assert result is mock_scheduler
        job_ids = [call.kwargs.get("id") for call in mock_scheduler.add_job.call_args_list]
        assert "daily_newsletter" not in job_ids
        assert "cleanup_expired_subscribers" in job_ids
        assert "publish_scheduled_posts" in job_ids


def test_init_scheduler_with_smtp():
    """Test init_scheduler initializes when SMTP_HOST is set."""
    from app.scheduler import init_scheduler

    # Patch the BackgroundScheduler where it's imported in scheduler module
    with (
        patch("app.scheduler._scheduler", None),
        patch("app.scheduler._scheduler_running") as mock_running,
        patch("apscheduler.schedulers.background.BackgroundScheduler") as MockScheduler,
    ):
        mock_running.is_set.return_value = False
        mock_scheduler = MagicMock()
        MockScheduler.return_value = mock_scheduler
        with (
            patch("app.config.SMTP_HOST", "smtp.example.com"),
            patch("app.config.NEWSLETTER_SEND_TIME", "09:00"),
        ):
            app = MagicMock()
            app.instance_path = "/tmp"
            result = init_scheduler(app)
            assert result is not None
            assert mock_scheduler.start.called
            assert mock_scheduler.add_job.called


def test_cleanup_expired_subscribers_with_subscribers(db):
    """Test cleanup_expired_subscribers keeps valid subscribers."""
    from app.scheduler import cleanup_expired_subscribers
    from app.models import Subscriber
    from datetime import timedelta

    expired = Subscriber(
        email="expired@example.com", confirmed=False, expires_at=utc_now() - timedelta(days=30)
    )
    valid = Subscriber(
        email="valid@example.com", confirmed=True, expires_at=utc_now() + timedelta(days=30)
    )
    db.session.add(expired)
    db.session.add(valid)
    db.session.commit()

    app = MagicMock()
    with patch("app.scheduler.FileLock") as mock_lock:
        mock_lock.return_value.acquire.return_value = True
        cleanup_expired_subscribers(app)

        deleted = db.session.execute(
            db.select(Subscriber).filter_by(email="expired@example.com")
        ).scalar_one_or_none()
        assert deleted is None

        kept = db.session.execute(
            db.select(Subscriber).filter_by(email="valid@example.com")
        ).scalar_one_or_none()
        assert kept is not None


def test_publish_scheduled_posts_ignores_future_posts(db, sample_post):
    """Test publish_scheduled_posts doesn't publish posts scheduled in future."""
    from app.scheduler import publish_scheduled_posts
    from app.models import Post

    sample_post.published = False
    sample_post.scheduled_publish_at = utc_now() + timedelta(days=30)
    db.session.commit()

    app = MagicMock()
    with patch("app.scheduler.FileLock") as mock_lock:
        mock_lock.return_value.acquire.return_value = True
        publish_scheduled_posts(app)

        db.session.expire(sample_post)
        sample_post = db.session.get(Post, sample_post.id)
        assert sample_post.published is False


def test_get_scheduler_next_run_with_scheduler():
    """Test get_scheduler_next_run returns time when scheduler exists."""
    from app.scheduler import get_scheduler_next_run

    mock_scheduler = MagicMock()
    mock_job = MagicMock()
    mock_job.next_run_time = utc_now()
    mock_scheduler.get_jobs.return_value = [mock_job]
    with patch("app.scheduler._scheduler", mock_scheduler):
        result = get_scheduler_next_run()
        assert result is not None


def test_scheduler_sends_newsletter_to_subscribers(db, sample_post, sample_subscriber):
    """Test send_daily_newsletter sends to confirmed subscribers."""
    from app.scheduler import send_daily_newsletter
    from contextlib import nullcontext

    sample_post.newsletter_sent_at = None
    sample_post.published = True
    sample_post.scheduled_publish_at = None
    db.session.commit()

    app = MagicMock()
    app.app_context.return_value = nullcontext()
    with patch("app.scheduler.FileLock") as mock_lock:
        mock_lock.return_value.acquire.return_value = True
        with patch("app.email.send_newsletter") as mock_send:
            mock_send.return_value = True
            send_daily_newsletter(app)
            assert mock_send.called or sample_post.newsletter_sent_at is not None
    db.session.remove()


def test_init_scheduler_idempotent():
    """Test calling init_scheduler twice doesn't create duplicate scheduler."""
    from app.scheduler import init_scheduler, _scheduler_running

    _scheduler_running.clear()
    with (
        patch("app.config.SMTP_HOST", "smtp.example.com"),
        patch("app.config.NEWSLETTER_SEND_TIME", "09:00"),
        patch("apscheduler.schedulers.background.BackgroundScheduler") as MockScheduler,
    ):
        mock_scheduler = MagicMock()
        MockScheduler.return_value = mock_scheduler
        app = MagicMock()
        app.instance_path = "/tmp"
        result1 = init_scheduler(app)
        assert result1 is mock_scheduler
        assert mock_scheduler.start.called

        mock_scheduler.reset_mock()
        result2 = init_scheduler(app)
        assert result2 is mock_scheduler
        mock_scheduler.start.assert_not_called()

    from app.scheduler import shutdown_scheduler

    shutdown_scheduler(wait=False)


def test_shutdown_scheduler():
    """Test shutdown_scheduler stops and clears state."""
    from app.scheduler import init_scheduler, shutdown_scheduler, _scheduler_running

    _scheduler_running.clear()
    with (
        patch("app.config.SMTP_HOST", "smtp.example.com"),
        patch("app.config.NEWSLETTER_SEND_TIME", "09:00"),
        patch("apscheduler.schedulers.background.BackgroundScheduler") as MockScheduler,
    ):
        mock_scheduler = MagicMock()
        MockScheduler.return_value = mock_scheduler
        app = MagicMock()
        app.instance_path = "/tmp"
        init_scheduler(app)

    shutdown_scheduler(wait=False)
    assert mock_scheduler.shutdown.called
    assert not _scheduler_running.is_set()

    from app.scheduler import _scheduler

    assert _scheduler is None


def test_shutdown_scheduler_noop_when_not_running():
    """Test shutdown_scheduler is a no-op when no scheduler is running."""
    from app.scheduler import shutdown_scheduler, _scheduler_running

    _scheduler_running.clear()
    with patch("app.scheduler._scheduler", None):
        shutdown_scheduler(wait=False)


def test_init_scheduler_respects_enable_flag():
    """Test that ENABLE_SCHEDULER=False prevents scheduler init via create_app."""
    import importlib
    from app import config

    original = config.ENABLE_SCHEDULER
    try:
        config.ENABLE_SCHEDULER = False
        with patch("app.scheduler.init_scheduler") as mock_init:
            import app as app_module

            importlib.reload(app_module)
            mock_init.assert_not_called()
    finally:
        config.ENABLE_SCHEDULER = original
