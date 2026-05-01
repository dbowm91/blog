"""Webhook delivery system with SSRF protection."""

import hashlib
import hmac
import json
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING

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

    Args:
        webhook_url: The URL to deliver the webhook to
        payload: The payload to send
        secret: The secret for HMAC signing

    Returns:
        A tuple of (success: bool, message: str)
    """
    import requests
    from app.utils import is_safe_webhook_url

    # SSRF protection: validate URL before making request
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
            allow_redirects=False,  # Prevent redirect-based SSRF
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
    from app.utils import utc_now

    event = WebhookEvent(
        event_type=event_type,
        payload=payload,
        target_id=target_id,
        target_type=target_type,
    )
    db.session.add(event)
    db.session.commit()

    try:
        from app.tasks import deliver_webhook_task
        deliver_webhook_task.delay(event.id)
    except Exception:
        pass

    return event.id


def init_webhooks(app: "Flask") -> None:
    """Initialize webhook system (placeholder for future integrations)."""
    pass
