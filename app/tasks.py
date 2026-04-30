"""Celery tasks for heavy operations."""

from celery import shared_task
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from celery import Celery

__all__ = [
    "generate_image_variants",
    "send_newsletter_task",
    "deliver_webhook_task",
]


@shared_task(bind=True, max_retries=3)
def generate_image_variants(self, filename: str) -> bool:
    """Generate responsive image variants for an image file.

    Generates 400w, 800w, 1200w variants in WebP and original format.
    Matches the naming convention used by _generate_responsive_variants_local.
    """
    from PIL import Image
    import os
    from app.storage import get_storage

    storage = get_storage()
    try:
        if storage.__class__.__name__ == "LocalStorageBackend":
            upload_folder = os.environ.get(
                "UPLOAD_FOLDER",
                os.path.join(os.path.dirname(__file__), "static", "uploads"),
            )
            filepath = os.path.join(upload_folder, filename)
            if not os.path.exists(filepath):
                return False

            ext = os.path.splitext(filepath)[1].lower().lstrip(".")
            basename = os.path.splitext(os.path.basename(filepath))[0]

            with Image.open(filepath) as img:
                for width in (400, 800, 1200):
                    if img.width > width:
                        ratio = width / img.width
                        new_height = int(img.height * ratio)
                        resized = img.resize((width, new_height), Image.Resampling.LANCZOS)
                    else:
                        resized = img.copy()

                    webp_filename = f"{width}_{basename}.webp"
                    webp_path = os.path.join(upload_folder, webp_filename)
                    resized.save(webp_path, format="WEBP", optimize=True)

                    if ext != "webp":
                        variant_filename = f"{width}_{basename}.{ext}"
                        variant_path = os.path.join(upload_folder, variant_filename)
                        resized.save(variant_path, optimize=True)
        elif storage.__class__.__name__ == "S3StorageBackend":
            # For S3, download the file first, process locally, then re-upload
            import tempfile
            from botocore.exceptions import ClientError, BotoCoreError

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = os.path.join(tmpdir, filename)
                file_data = storage.load(filename)
                if not file_data:
                    return False
                with open(tmp_path, "wb") as f:
                    f.write(file_data)

                ext = os.path.splitext(tmp_path)[1].lower().lstrip(".")
                basename = os.path.splitext(os.path.basename(tmp_path))[0]

                with Image.open(tmp_path) as img:
                    for width in (400, 800, 1200):
                        if img.width > width:
                            ratio = width / img.width
                            new_height = int(img.height * ratio)
                            resized = img.resize((width, new_height), Image.Resampling.LANCZOS)
                        else:
                            resized = img.copy()

                        webp_filename = f"{width}_{basename}.webp"
                        webp_path = os.path.join(tmpdir, webp_filename)
                        resized.save(webp_path, format="WEBP", optimize=True)

                        if ext != "webp":
                            variant_filename = f"{width}_{basename}.{ext}"
                            variant_path = os.path.join(tmpdir, variant_filename)
                            resized.save(variant_path, optimize=True)

                # Upload all generated variants
                storage.save(filename, file_data)
                for width in (400, 800, 1200):
                    webp_variant_name = f"{width}_{basename}.webp"
                    webp_variant_path = os.path.join(tmpdir, webp_variant_name)
                    if os.path.exists(webp_variant_path):
                        with open(webp_variant_path, "rb") as f:
                            storage.save(webp_variant_name, f.read())

                    if ext != "webp":
                        variant_name = f"{width}_{basename}.{ext}"
                        variant_path = os.path.join(tmpdir, variant_name)
                        if os.path.exists(variant_path):
                            with open(variant_path, "rb") as f:
                                storage.save(variant_name, f.read())

        return True
    except (ClientError, BotoCoreError) as e:
        logger.error("S3 operation failed: %s", e)
        return False
    except Exception as e:
        logger.error("Image variant generation failed: %s", e)
        return False


@shared_task(bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def send_newsletter_task(self, post_ids: List[int]) -> bool:
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


@shared_task(bind=True, max_retries=3)
def deliver_webhook_task(self, webhook_event_id: int) -> bool:
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
