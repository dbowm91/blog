import os

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

_scheduler_running = False


def get_scheduler_status():
    """Return whether the scheduler is running."""
    return _scheduler_running


def send_daily_newsletter(app):
    lock_path = os.path.join(app.instance_path, "newsletter.lock")
    lock_file = None
    try:
        lock_file = open(lock_path, "w")
        if HAS_FCNTL:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        if lock_file:
            lock_file.close()
        return

    try:
        with app.app_context():
            from app.models import Post, Subscriber
            from app.email import send_newsletter
            from app.extensions import db
            from app.utils import utc_now
            from app.config import NEWSLETTER_MAX_RETRY_ATTEMPTS

            posts = (
                Post.query.filter(
                    Post.published == True,
                    Post.published_at != None,
                    Post.newsletter_sent_at == None,
                    Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS,
                )
                .order_by(Post.published_at.desc())
                .all()
            )

            if not posts:
                return

            subscribers = Subscriber.query.filter_by(confirmed=True).filter(
                Subscriber.unsubscribed_at.is_(None)
            ).all()
            if not subscribers:
                return

            success = send_newsletter(posts, subscribers)

            if success:
                now = utc_now()
                for post in posts:
                    post.newsletter_sent_at = now
                    post.newsletter_attempts = 0
                db.session.commit()
            else:
                for post in posts:
                    post.newsletter_attempts = (post.newsletter_attempts or 0) + 1
                db.session.commit()
                app.logger.warning("Newsletter had failures; %d posts will be retried (attempts incremented)", len(posts))
    finally:
        if lock_file:
            if HAS_FCNTL:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            try:
                os.remove(lock_path)
            except FileNotFoundError:
                pass


def cleanup_expired_subscribers(app):
    """Remove unconfirmed subscribers whose confirmation window has expired."""
    lock_path = os.path.join(app.instance_path, "cleanup.lock")
    lock_file = None
    try:
        lock_file = open(lock_path, "w")
        if HAS_FCNTL:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        if lock_file:
            lock_file.close()
        return

    try:
        with app.app_context():
            from app.models import Subscriber
            from app.extensions import db
            from app.utils import utc_now

            expired = Subscriber.query.filter(
                Subscriber.confirmed == False,
                Subscriber.expires_at != None,
                Subscriber.expires_at < utc_now(),
            ).all()

            if not expired:
                return

            for sub in expired:
                db.session.delete(sub)
            db.session.commit()
            app.logger.info("Cleaned up %d expired unconfirmed subscribers", len(expired))
    finally:
        if lock_file:
            if HAS_FCNTL:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            try:
                os.remove(lock_path)
            except FileNotFoundError:
                pass


def init_scheduler(app):
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
    scheduler.start()
    global _scheduler_running
    _scheduler_running = True
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler
