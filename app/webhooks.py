"""Webhook delivery system with SSRF protection."""

import hashlib
import hmac
import json
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from requests.exceptions import RequestException

if TYPE_CHECKING:
    from flask import Flask

__all__ = [
    "WebhookDeliveryError",
    "sign_webhook_payload",
    "deliver_webhook",
    "create_webhook_event",
    "init_webhooks",
]

WEBHOOK_TIMEOUT = 10


class WebhookDeliveryError(Exception):
    """Raised when webhook delivery fails."""
    pass


def sign_webhook_payload(payload: Dict[str, Any], secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def deliver_webhook(webhook_url: str, payload: Dict[str, Any], secret: str) -> Tuple[bool, str]:
    """Deliver a webhook to a single URL with signature header and SSRF protection.

    .. deprecated::
        This function is deprecated. Use :func:`app.tasks.deliver_webhook_task` instead,
        which handles all delivery with proper async processing and SSRF protection.

    Args:
        webhook_url: The URL to deliver the webhook to
        payload: The payload to send
        secret: The secret for HMAC signing

    Returns:
        A tuple of (success: bool, message: str)
    """
    import warnings
    warnings.warn(
        "deliver_webhook() is deprecated. Use deliver_webhook_task instead.",
        DeprecationWarning,
        stacklevel=2
    )
    import requests
    from app.utils import is_safe_webhook_url

    is_safe, reason = is_safe_webhook_url(webhook_url)
    if not is_safe:
        return False, f"SSRF protection: {reason}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Blog-CMS-Webhook/1.0",
        "X-Webhook-Signature": sign_webhook_payload(payload, secret),
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT,
            allow_redirects=False,
        )
        return response.status_code < 400, f"HTTP {response.status_code}"
    except requests.RequestException as e:
        return False, str(e)


def create_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
    target_id: Optional[int] = None,
    target_type: Optional[str] = None,
) -> int:
    """Create a webhook event record and schedule delivery."""
    from app.extensions import db
    from app.models import WebhookEvent

    event = WebhookEvent(
        event_type=event_type,
        payload=payload,
        target_id=target_id,
        target_type=target_type,
    )
    db.session.add(event)
    db.session.commit()

    event_id = int(event.id)

    try:
        from app.tasks import deliver_webhook_task
        deliver_webhook_task.delay(event_id)
    except (RequestException, ValueError, OSError) as e:
        logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)

    return event_id


def init_webhooks(app: "Flask") -> None:
    """Initialize webhook system (placeholder for future integrations)."""
    pass
