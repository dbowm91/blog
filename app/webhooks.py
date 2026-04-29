"""Webhook delivery system."""

import hashlib
import hmac
import json
from typing import Optional, Dict, Any, List, TYPE_CHECKING

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


def deliver_webhook(webhook_url: str, payload: Dict[str, Any], secret: str) -> bool:
    """Deliver a webhook to a single URL with signature header."""
    import requests

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
        )
        return response.status_code < 400
    except requests.RequestException:
        return False


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
