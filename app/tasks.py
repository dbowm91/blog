"""Celery tasks for heavy operations."""

import logging
import os
from typing import List, Any, TYPE_CHECKING

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, Retry
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import http_client
from app.webhooks import sign_webhook_payload

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = [
    "generate_image_variants",
    "send_newsletter_task",
    "deliver_webhook_task",
    "deliver_single_webhook_task",
    "send_confirmation_task",
    "send_password_reset_task",
    "run_backup_task",
    "notify_pending_comment_task",
]


@shared_task(bind=True, queue="images")
def generate_image_variants(self: Any, filename: str) -> bool:
    """Generate responsive image variants for an image file.

    Generates 400w, 800w, 1200w variants in WebP and original format.
    Matches the naming convention used by _generate_responsive_variants_local.
    """
    from PIL import Image
    from app.extensions import db
    from app.storage import get_storage, LocalStorageBackend, S3StorageBackend

    storage = get_storage()
    try:
        if isinstance(storage, LocalStorageBackend):
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
        elif isinstance(storage, S3StorageBackend):
            import tempfile
            from botocore.exceptions import ClientError, BotoCoreError

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = os.path.join(tmpdir, filename)
                try:
                    response = storage.client.get_object(Bucket=storage.bucket, Key=filename)
                    with open(tmp_path, "wb") as f:
                        for chunk in response["Body"].iter_chunks():
                            f.write(chunk)
                except (ClientError, BotoCoreError):
                    return False
                if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                    return False

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
    except (SQLAlchemyError, OSError, ImportError) as e:
        logger.error("Image variant generation failed: %s", e)
        return False
    finally:
        db.session.remove()


@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=540,
    queue="newsletter",
)
def send_newsletter_task(self: Any, post_ids: List[int]) -> bool:
    """Send newsletter for specified posts (async).

    Celery max_retries=3 controls task-level retries. Per-email retries are
    handled inside send_newsletter via NEWSLETTER_MAX_RETRY_ATTEMPTS (default 5).
    """
    from app.config import NEWSLETTER_MAX_RETRY_ATTEMPTS
    from app.email import send_newsletter
    from app.extensions import db
    from app.models import Post, Subscriber
    from sqlalchemy import func, select

    try:
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

        stmt = (
            select(Subscriber)
            .filter_by(confirmed=True)
            .filter(Subscriber.unsubscribed_at.is_(None))
        )
        subscribers = db.session.execute(stmt).scalars().all()

        success = send_newsletter(posts, subscribers, subscriber_count)

        if success:
            from app.utils import utc_now

            now = utc_now()
            for post in posts:
                if post is not None:
                    post.newsletter_sent_at = now
                    post.newsletter_attempts = 0
            db.session.commit()
        else:
            last_attempts = 0
            for post in posts:
                if post is not None:
                    post.newsletter_attempts = min(
                        (post.newsletter_attempts or 0) + 1, NEWSLETTER_MAX_RETRY_ATTEMPTS
                    )
                    last_attempts = post.newsletter_attempts
            db.session.commit()
            logger.warning(
                "Newsletter task failed for %d posts (attempts incremented to %d)",
                len(posts),
                last_attempts,
            )
            self.retry()

        return success
    finally:
        db.session.remove()


@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="webhooks")
def deliver_webhook_task(self: Any, webhook_event_id: int) -> bool:
    """Deliver a webhook event to registered endpoints with SSRF protection and HMAC signing.

    This task dispatches individual webhook deliveries to deliver_single_webhook_task
    for per-webhook retry support. Each webhook gets its own Celery task invocation
    with independent retry logic.
    """
    from app.extensions import db
    from app.models import Webhook, WebhookEvent

    try:
        event = db.session.get(WebhookEvent, webhook_event_id)
        if not event or event.delivered:
            return False

        webhooks = (
            db.session.execute(select(Webhook).filter_by(enabled=True, event_type=event.event_type))
            .scalars()
            .all()
        )

        if not webhooks:
            event.delivered = True
            db.session.commit()
            return True

        # Collect IDs before dispatch to avoid DetachedInstanceError under
        # eager Celery execution where child task may close the session.
        webhook_ids = [w.id for w in webhooks]

        # Dispatch individual webhook deliveries for per-webhook retry
        for webhook_id in webhook_ids:
            deliver_single_webhook_task.delay(webhook_event_id, webhook_id)

        return True
    finally:
        db.session.remove()


@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="webhooks")
def deliver_single_webhook_task(self: Any, webhook_event_id: int, webhook_id: int) -> bool:
    """Deliver a webhook event to a single endpoint with per-webhook retry.

    This task handles delivery to a single webhook with independent retry logic.
    Failed deliveries will be retried up to 3 times with exponential backoff.
    """
    from app.extensions import db
    from app.models import Webhook, WebhookEvent
    from app.config import WEBHOOK_TIMEOUT
    from app.utils import is_safe_webhook_url

    event = None
    webhook = None

    try:
        event = db.session.get(WebhookEvent, webhook_event_id)
        webhook = db.session.get(Webhook, webhook_id)

        if not event or not webhook:
            return False

        # SSRF Protection: validate URL before making request
        is_safe, reason = is_safe_webhook_url(webhook.url)
        if not is_safe:
            from urllib.parse import urlparse

            hostname = urlparse(webhook.url).hostname or "unknown"
            logger.warning(
                "SSRF protection blocked webhook %d (host=%s): %s",
                webhook.id,
                hostname,
                reason,
            )
            event.delivery_attempts += 1
            event.failed_deliveries += 1
            db.session.commit()
            return False

        # Get the webhook secret (already decrypted via property)
        secret = webhook.secret
        if not secret:
            logger.warning("No secret configured for webhook %s, skipping", webhook.name)
            event.delivery_attempts += 1
            event.failed_deliveries += 1
            db.session.commit()
            return False

        # Prepare headers with HMAC signature
        payload = event.payload
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Blog-CMS-Webhook/1.0",
            "X-Webhook-Signature": sign_webhook_payload(payload, secret),
        }

        try:
            response = http_client.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT,
                allow_redirects=False,  # Prevent redirect-based SSRF
            )
            try:
                event.delivery_attempts += 1

                if response.status_code < 400:
                    event.successful_deliveries += 1
                    db.session.commit()
                    _update_delivery_status(event, db)
                    return True
                logger.warning("Webhook %s returned HTTP %d", webhook.name, response.status_code)
                db.session.commit()
                raise self.retry(
                    exc=http_client.RequestException(f"HTTP {response.status_code}")
                )
            finally:
                response.close()
        except http_client.RequestException as e:
            event.delivery_attempts += 1
            db.session.commit()
            raise self.retry(exc=e)
    except MaxRetriesExceededError:
        webhook_name = webhook.name if webhook else "unknown"
        event_obj = db.session.get(WebhookEvent, webhook_event_id) if webhook_event_id else None
        if event_obj is not None:
            event_obj.failed_deliveries += 1
            _update_delivery_status(event_obj, db)
        logger.error("Webhook delivery to %s failed after max retries", webhook_name)
        return False
    except Retry:
        raise
    except Exception as e:
        webhook_name = webhook.name if webhook else "unknown"
        event_obj = db.session.get(WebhookEvent, webhook_event_id) if webhook_event_id else None
        if event_obj is not None:
            event_obj.failed_deliveries += 1
            _update_delivery_status(event_obj, db)
        logger.error("Unexpected error delivering webhook to %s: %s", webhook_name, e)
        return False
    finally:
        db.session.remove()


def _update_delivery_status(event: Any, db: Any) -> None:
    """Update the delivery_status field based on per-webhook delivery results."""
    from app.models import Webhook

    concurrency = os.environ.get("CELERYD_CONCURRENCY")
    if concurrency is not None:
        try:
            concurrency_int = int(concurrency)
            if concurrency_int > 1:
                logger.warning(
                    "Celery concurrency is %d (>1). "
                    "_update_delivery_status() uses in-memory state and may produce incorrect results. "
                    "Use --concurrency=1 for webhook delivery workers.",
                    concurrency_int,
                )
        except ValueError:
            pass

    webhooks = (
        db.session.execute(select(Webhook).filter_by(enabled=True, event_type=event.event_type))
        .scalars()
        .all()
    )

    total_count = len(webhooks)
    if total_count == 0:
        event.delivery_status = None
        return

    completed_count = event.successful_deliveries + event.failed_deliveries
    if completed_count < total_count:
        return

    if event.successful_deliveries == total_count:
        event.delivery_status = "delivered"
        event.delivered = True
    elif event.failed_deliveries == total_count:
        event.delivery_status = "failed"
        event.delivered = False
    else:
        event.delivery_status = "partial_failure"
        event.delivered = True

    db.session.commit()


@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="email")
def send_confirmation_task(self: Any, subscriber_id: int) -> bool:
    """Send confirmation email to a subscriber asynchronously."""
    from app.extensions import db
    from app.models import Subscriber
    from app.email import send_confirmation

    try:
        subscriber = db.session.get(Subscriber, subscriber_id)
        if not subscriber:
            return False

        send_confirmation(subscriber)
        return True
    except Exception as e:
        logger.error(f"Confirmation email failed: {e}")
        raise self.retry(exc=e)
    finally:
        db.session.remove()


@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="email")
def send_password_reset_task(self: Any, user_id: int, token: str) -> bool:
    """Send password reset email to a user asynchronously."""
    from app.extensions import db
    from app.models import User
    from app.email import send_password_reset

    try:
        user = db.session.get(User, user_id)
        if not user:
            return False

        send_password_reset(user, token)
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        raise self.retry(exc=e)
    finally:
        db.session.remove()


@shared_task(bind=True, queue="backup")
def run_backup_task(self: Any) -> bool:
    """Run database backup asynchronously to avoid blocking web requests."""
    from app.extensions import db
    from app.services.backup import create_backup

    try:
        from flask import current_app

        from app.services.backup import resolve_backup_dir, resolve_database_file

        backup_dir = resolve_backup_dir(current_app)
        db_path = resolve_database_file(current_app)
        if not db_path:
            return False

        result = create_backup(db_path, backup_dir, compress=True, keep=7, encrypt=False)
        return result is not None
    except (SQLAlchemyError, OSError, ImportError) as e:
        logger.error("Backup task failed: %s", e)
        return False
    finally:
        db.session.remove()


@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="email")
def notify_pending_comment_task(self: Any, comment_id: int) -> bool:
    """Notify admins of a pending comment awaiting moderation."""
    from app.extensions import db
    from app.models import Comment, User
    from app.email import _send_email

    try:
        comment = db.session.get(Comment, comment_id)
        if not comment:
            return False

        post_title = comment.post.title if comment.post else "Unknown post"
        subject = f"New pending comment on '{post_title}'"
        body = (
            f"A new comment is awaiting moderation:\n\n"
            f"Author: {comment.author_name} <{comment.author_email}>\n"
            f"Post: {post_title}\n\n"
            f"{comment.content}\n\n"
            f"Approve or delete it at /admin/comments"
        )

        admins = db.session.execute(select(User).filter_by(is_admin=True)).scalars().all()
        for admin in admins:
            if admin.email:
                _send_email(admin.email, subject, body)

        return True
    except (SQLAlchemyError, OSError, ImportError) as e:
        logger.error("Pending comment notification failed: %s", e)
        return False
    finally:
        db.session.remove()
