from datetime import datetime, timedelta, timezone


def send_daily_newsletter(app):
    with app.app_context():
        from app.models import Post, Subscriber
        from app.email import send_newsletter

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        posts = (
            Post.query.filter(
                Post.published == True,
                Post.published_at != None,
                Post.published_at >= yesterday,
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
