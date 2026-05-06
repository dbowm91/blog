# Webhooks (`app/webhooks.py`)

Webhook delivery system with SSRF protection and HMAC signing.

## Features

- **HMAC-SHA256 Signing**: `X-Webhook-Signature` header
- **SSRF Protection**: URL validation against private IP ranges
- **Async Delivery**: Via Celery task queue
- **Retry Logic**: Exponential backoff via Celery

## Webhook Model

```python
class Webhook(db.Model):
    name = db.Column(db.String(100))
    url = db.Column(db.String(512))
    secret = db.Column(db.String(64))  # Encrypted
    event_type = db.Column(db.String(32))  # post.published, post.created, etc.
    enabled = db.Column(db.Boolean, default=True)

class WebhookEvent(db.Model):
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhooks.id"))
    event_type = db.Column(db.String(32))
    payload = db.Column(db.JSON)  # Event data
    target_id = db.Column(db.Integer)  # Related object ID
    target_type = db.Column(db.String(32))  # "post", "subscriber", etc.
    delivered = db.Column(db.Boolean, default=False)
    delivery_attempts = db.Column(db.Integer, default=0)
```

## Core Functions

### `sign_webhook_payload()`

```python
def sign_webhook_payload(payload: Dict[str, Any], secret: str) -> str:
```

Generates HMAC-SHA256 signature:
```python
signature = hmac.new(
    secret.encode("utf-8"),
    json.dumps(payload, sort_keys=True).encode("utf-8"),
    hashlib.sha256
).hexdigest()
return f"sha256={signature}"
```

### `deliver_webhook()`

```python
def deliver_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    secret: str
) -> Tuple[bool, str]:
```

Delivers to single URL with:
- SSRF validation via `is_safe_webhook_url()`
- HMAC signature header
- 10 second timeout
- No redirects allowed

### `create_webhook_event()`

```python
def create_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
    target_id: Optional[int] = None,
    target_type: Optional[str] = None
) -> int:
```

Creates `WebhookEvent` record and queues `deliver_webhook_task` Celery task.

## SSRF Protection

The `is_safe_webhook_url()` utility validates:
- No private IP ranges (10.x, 172.16.x, 192.168.x)
- No link-local addresses
- No loopback addresses
- No IPv6 equivalents

## Event Types

| Event | Trigger |
|-------|---------|
| `post.published` | Post goes live |
| `post.created` | New post created |
| `subscriber.confirmed` | New subscriber confirms |

## See Also
- [Celery Tasks](../tasks/celery-tasks.md) - Async delivery
- [Webhook Encryption](../deployment/security.md) - Secret encryption
