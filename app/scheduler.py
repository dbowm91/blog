import fcntl
import os


def send_daily_newsletter(app):
    lock_path = os.path.join(app.instance_path, "newsletter.lock")
    try:
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        return

    try:
        with app.app_context():
            from app.models import Post, Subscriber
            from app.email import send_newsletter
            from app.extensions import db
            from app.utils import utc_now

            posts = (
                Post.query.filter(
                    Post.published == True,
                    Post.published_at != None,
                    Post.newsletter_sent_at == None,
                )
                .order_by(Post.published_at.desc())
                .all()
            )

            if not posts:
                return

            subscribers = Subscriber.query.filter_by(confirmed=True).all()
            if not subscribers:
                return

            send_newsletter(posts, subscribers)

            now = utc_now()
            for post in posts:
                post.newsletter_sent_at = now
            db.session.commit()
    finally:
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

    from app.config import NEWSLETTER_SEND_TIME

    hour, minute = map(int, NEWSLETTER_SEND_TIME.split(":"))

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        send_daily_newsletter,
        CronTrigger(hour=hour, minute=minute),
        args=[app],
        id="daily_newsletter",
        replace_existing=True,
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler
