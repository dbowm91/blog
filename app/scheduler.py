"""APScheduler newsletter scheduler with file locking.

Multi-worker limitation:
    The scheduler runs in-process with filelock to prevent duplicate
    newsletter sends on a single machine. This does NOT protect across multiple
    machines (e.g., container clusters). For multi-machine deployments, use an
    external scheduler (cron, Celery Beat) or distributed lock (Redis, etcd).
    See DEPLOY.md section 4 for details.
"""

import os
import threading
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import func, select, delete

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

__all__ = [
    "init_scheduler",
    "get_scheduler_status",
    "get_scheduler_health",
    "get_scheduler_next_run",
]

from filelock import FileLock, Timeout as FileLockTimeout

_scheduler_running = threading.Event()
_scheduler: Optional["BackgroundScheduler"] = None
_last_newsletter_send_lock = threading.Lock()
_last_newsletter_send: Optional[datetime] = None


def get_scheduler_status() -> bool:
    """Return whether the scheduler is running."""
    return _scheduler_running.is_set()


def get_scheduler_next_run() -> Optional[datetime]:
    """Return the next scheduled run time, or None if not running/scheduled."""
    global _scheduler
    if _scheduler is None:
        return None
    try:
        jobs = _scheduler.get_jobs()
        if not jobs:
            return None
        next_job = min(jobs, key=lambda j: j.next_run_time)
        return next_job.next_run_time
    except (AttributeError, KeyError, ValueError):
        return None


def get_scheduler_health() -> dict:
    """Return scheduler health info for monitoring."""
    global _last_newsletter_send
    running = _scheduler_running.is_set()
    with _last_newsletter_send_lock:
        last_send = _last_newsletter_send
    next_run = get_scheduler_next_run()
    return {
        "status": "running" if running else "stopped",
        "last_newsletter_send": last_send.isoformat() if last_send else None,
        "next_run": next_run.isoformat() if next_run else None,
    }


def send_daily_newsletter(app) -> None:
    lock_path = os.path.join(app.instance_path, "newsletter.lock")
    lock = FileLock(lock_path, timeout=0)
    try:
        lock.acquire()
    except FileLockTimeout:
        return

    try:
        with app.app_context():
            from app.models import Post, Subscriber
            from app.email import send_newsletter
            from app.extensions import db
            from app.utils import utc_now
            from app.config import NEWSLETTER_MAX_RETRY_ATTEMPTS

            posts = (
                db.session.execute(
                    select(Post)
                    .filter(
                        Post.published,
                        Post.published_at is not None,
                        Post.newsletter_sent_at is None,
                        Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS,
                    )
                    .order_by(Post.published_at.desc())
                )
                .scalars()
                .all()
            )

            if not posts:
                return

            subscriber_count = db.session.execute(
                select(func.count(Subscriber.id))
                .filter_by(confirmed=True)
                .filter(Subscriber.unsubscribed_at.is_(None))
            ).scalar_one_or_none()

            if not subscriber_count:
                app.logger.info("No subscribers to send newsletter to")
                return

            subscribers = db.session.execute(
                select(Subscriber)
                .filter_by(confirmed=True)
                .filter(Subscriber.unsubscribed_at.is_(None))
                .yield_per(500)
            ).scalars()

            success = send_newsletter(posts, subscribers, subscriber_count)

            if success:
                now = utc_now()
                for post in posts:
                    post.newsletter_sent_at = now
                    post.newsletter_attempts = 0
                db.session.commit()
                global _last_newsletter_send
                with _last_newsletter_send_lock:
                    _last_newsletter_send = now
            else:
                for post in posts:
                    post.newsletter_attempts = (post.newsletter_attempts or 0) + 1
                db.session.commit()
                app.logger.warning(
                    "Newsletter had failures; %d posts will be retried (attempts incremented)",
                    len(posts),
                )
    finally:
        lock.release()


def cleanup_expired_subscribers(app) -> None:
    """Remove unconfirmed subscribers whose confirmation window has expired."""
    lock_path = os.path.join(app.instance_path, "cleanup.lock")
    lock = FileLock(lock_path, timeout=0)
    try:
        lock.acquire()
    except FileLockTimeout:
        return

    try:
        with app.app_context():
            from app.models import Subscriber
            from app.extensions import db
            from app.utils import utc_now

            expired = (
                db.session.execute(
                    select(Subscriber).filter(
                        not Subscriber.confirmed,
                        Subscriber.expires_at is not None,
                        Subscriber.expires_at < utc_now(),
                    )
                )
                .scalars()
                .all()
            )

            if not expired:
                return

            db.session.execute(
                delete(Subscriber).where(
                    Subscriber.id.in_([sub.id for sub in expired])
                )
            )
            db.session.commit()
            app.logger.info(
                "Cleaned up %d expired unconfirmed subscribers", len(expired)
            )
    finally:
        lock.release()


def publish_scheduled_posts(app) -> None:
    """Auto-publish posts whose scheduled_publish_at time has passed."""
    lock_path = os.path.join(app.instance_path, "scheduled.lock")
    lock = FileLock(lock_path, timeout=0)
    try:
        lock.acquire()
    except FileLockTimeout:
        return

    try:
        with app.app_context():
            from app.models import Post
            from app.extensions import db
            from app.utils import utc_now
            from app.search import sync_fts_batch
            from app.tag_cache import invalidate_tag_cache

            now = utc_now()
            posts = (
                db.session.execute(
                    select(Post).filter(
                        not Post.published,
                        Post.scheduled_publish_at is not None,
                        Post.scheduled_publish_at <= now,
                    )
                )
                .scalars()
                .all()
            )

            if not posts:
                return

            fts_items = []
            for post in posts:
                post.published = True
                post.published_at = now
                post.scheduled_publish_at = None
                fts_items.append((post.id, post.title, post.body, post.summary, True))
            if not sync_fts_batch(fts_items):
                db.session.rollback()
                app.logger.warning("FTS sync failed during scheduled publish; rolling back %d posts", len(posts))
                return

            db.session.commit()
            invalidate_tag_cache()
            app.logger.info("Auto-published %d scheduled post(s)", len(posts))
    finally:
        lock.release()


BACKUP_RETENTION_COUNT = 7


def run_daily_backup(app) -> None:
    """Run daily database backup with retention cleanup."""
    from app.services.backup import run_daily_backup as _run_backup

    lock_path = os.path.join(app.instance_path, "backup.lock")
    lock = FileLock(lock_path, timeout=0)
    try:
        lock.acquire()
    except FileLockTimeout:
        return

    try:
        with app.app_context():
            _run_backup(app)
    finally:
        lock.release()


def init_scheduler(app) -> Optional["BackgroundScheduler"]:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import atexit

    from app.config import NEWSLETTER_SEND_TIME, SMTP_HOST

    if not SMTP_HOST:
        app.logger.info("SMTP_HOST not configured; newsletter scheduler disabled")
        return None

    hour, minute = map(int, NEWSLETTER_SEND_TIME.split(":"))

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        send_daily_newsletter,
        CronTrigger(hour=hour, minute=minute),
        args=[app],
        id="daily_newsletter",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_expired_subscribers,
        CronTrigger(minute="*/5"),
        args=[app],
        id="cleanup_expired_subscribers",
        replace_existing=True,
    )
    scheduler.add_job(
        publish_scheduled_posts,
        CronTrigger(minute="*/5"),
        args=[app],
        id="publish_scheduled_posts",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_backup,
        CronTrigger(hour=2, minute=0),
        args=[app],
        id="daily_backup",
        replace_existing=True,
    )
    scheduler.start()
    global _scheduler
    _scheduler = scheduler
    _scheduler_running.set()

    def _shutdown_scheduler():
        _scheduler_running.clear()
        scheduler.shutdown(wait=False)

    atexit.register(_shutdown_scheduler)
    return scheduler
