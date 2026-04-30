"""Celery tasks for heavy operations."""

from typing import Optional, List, TYPE_CHECKING
from celery import shared_task

if TYPE_CHECKING:
    from celery import Celery

__all__ = [
    "generate_image_variants",
    "send_newsletter_task",
    "deliver_webhook_task",
    "send_confirmation_task",
    "send_password_reset_task",
]


def generate_image_variants(image_path: str, post_id: int) -> bool:
    """Generate responsive image variants for a post image."""
    from app.storage import get_storage
    storage = get_storage()
    variants = [400, 800, 1200]
    try:
        if storage.__class__.__name__ == "LocalStorageBackend":
            from PIL import Image
            import os
            upload_folder = "app/static/uploads"
            full_path = os.path.join(upload_folder, image_path)
            if not os.path.exists(full_path):
                return False
            img = Image.open(full_path)
            for width in variants:
                height = int(img.height * (width / img.width))
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                name, ext = os.path.splitext(image_path)
                variant_path = os.path.join(upload_folder, f"{name}_{width}w{ext}")
                resized.save(variant_path, quality=85, optimize=True)
        return True
    except Exception:
        return False


def send_newsletter_task(post_ids: List[int]) -> bool:
    """Send newsletter for specified posts (async)."""
    from app.email import send_newsletter
    from app.extensions import db
    from app.models import Post, Subscriber
    from sqlalchemy import func, select

    posts = [db.session.get(Post, pid) for pid in post_ids]
    posts = [p for p in posts if p]

    if not posts:
        return False

    subscriber_count = db.session.execute(
        select(func.count(Subscriber.id))
        .filter_by(confirmed=True)
        .filter(Subscriber.unsubscribed_at.is_(None))
    ).scalar_one_or_none()

    if not subscriber_count:
        return False

    subscribers = db.session.execute(
        select(Subscriber)
        .filter_by(confirmed=True)
        .filter(Subscriber.unsubscribed_at.is_(None))
        .yield_per(500)
    ).scalars()

    success = send_newsletter(posts, subscribers, subscriber_count)

    if success:
        from app.utils import utc_now
        now = utc_now()
        for post in posts:
            post.newsletter_sent_at = now
            post.newsletter_attempts = 0
        db.session.commit()
    else:
        for post in posts:
            post.newsletter_attempts = (post.newsletter_attempts or 0) + 1
        db.session.commit()

    return success


def deliver_webhook_task(webhook_event_id: int) -> bool:
    """Deliver a webhook event to registered endpoints."""
    import requests
    from app.extensions import db
    from app.models import Webhook, WebhookEvent
    from app.config import WEBHOOK_TIMEOUT

    event = db.session.get(WebhookEvent, webhook_event_id)
    if not event or event.delivered:
        return False

    webhooks = db.session.execute(
        select(Webhook).filter_by(enabled=True, event_type=event.event_type)
    ).scalars().all()

    if not webhooks:
        event.delivered = True
        db.session.commit()
        return True

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Blog-CMS-Webhook/1.0",
    }
    payload = event.payload

    delivered_count = 0
    for webhook in webhooks:
        try:
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT,
            )
            event.delivery_attempts += 1
            if response.status_code < 400:
                delivered_count += 1
        except requests.RequestException:
            event.delivery_attempts += 1

    event.delivered = delivered_count > 0
    db.session.commit()
    return event.delivered


@shared_task(bind=True, max_retries=3)
def send_confirmation_task(self, subscriber_id: int) -> bool:
    """Send confirmation email to a subscriber asynchronously."""
    from app.extensions import db
    from app.models import Subscriber
    from app.email import send_confirmation

    subscriber = db.session.get(Subscriber, subscriber_id)
    if not subscriber:
        return False

    try:
        send_confirmation(subscriber)
        return True
    except Exception:
        return False


@shared_task(bind=True, max_retries=3)
def send_password_reset_task(self, user_id: int, token: str) -> bool:
    """Send password reset email to a user asynchronously."""
    from app.extensions import db
    from app.models import User
    from app.email import send_password_reset

    user = db.session.get(User, user_id)
    if not user:
        return False

    try:
        send_password_reset(user, token)
        return True
    except Exception:
        return False
