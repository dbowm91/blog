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
    webhook_secret_encrypted = db.Column(db.LargeBinary(256))  # AES-256-GCM encrypted
    event_type = db.Column(db.String(32))  # post.published, post.created, etc.
    enabled = db.Column(db.Boolean, default=True)

    @property
    def secret(self) -> str:
        """Decrypt and return the webhook secret."""
        # Uses app.webhook_encryption.py for AES-256-GCM decryption

class WebhookEvent(db.Model):
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhooks.id"))
    event_type = db.Column(db.String(32))
    payload = db.Column(db.JSON)  # Event data
    target_id = db.Column(db.Integer)  # Related object ID
    target_type = db.Column(db.String(32))  # "post", "subscriber", etc.
    delivered = db.Column(db.Boolean, default=False)
    delivery_status = db.Column(db.String(32))  # 'failed', 'partial_failure', 'delivered'
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
- `WEBHOOK_TIMEOUT` second timeout (configurable via `webhook.timeout` in config)
- No redirects allowed

**Deprecated:** This function is deprecated. All webhook deliveries should go through the `deliver_webhook_task` Celery task which handles async processing with proper retry logic and SSRF protection.

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

The `is_safe_webhook_url()` utility in `app/utils.py:312-414` performs extensive validation:

- **Scheme check**: Only `http://` and `https://` allowed
- **URL format validation**: Rejects userinfo (username/password) in URL
- **Loopback blocking**: 127.0.0.1, ::1, localhost, 0.0.0.0
- **IP validation**: Resolves hostname and validates IPs:
  - Loopback (127.0.0.0/8, ::1)
  - Private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  - Link-local (169.254.0.0/16, fe80::/10)
  - Reserved, multicast
  - Non-global (`ip.is_global` check)
- **IPv4-mapped IPv6**: Checks for `::ffff:` prefix and blocks mapped private/loopback IPs
- **Cloud metadata endpoints**:
  - AWS: 169.254.169.254
  - GCP: metadata.google.internal
- **Redirect blocking**: Both `deliver_webhook()` and `deliver_webhook_task` set `allow_redirects=False`

## Delivery Status Tracking

`WebhookEvent.delivery_status` tracks the outcome of webhook deliveries:

| Status | Meaning |
|--------|---------|
| `'delivered'` | All webhooks in the event succeeded |
| `'partial_failure'` | Some webhooks succeeded, some failed |
| `'failed'` | All webhooks in the event failed |

## Event Types

| Event | Trigger |
|-------|---------|
| `post.published` | Post goes live |
| `post.created` | New post created |
| `subscriber.confirmed` | New subscriber confirms |

## Queue Reference

Webhook delivery uses the `webhooks` Celery queue (see `app/tasks.py:184`).

Other queues used by the system:

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:31` |
| `newsletter` | Newsletter delivery | `app/tasks.py:130` |
| `webhooks` | Webhook delivery | `app/tasks.py:182` |
| `email` | Transactional email | `app/tasks.py:262,283` |
| `backup` | Backup tasks | `app/tasks.py:304` |

## See Also
- [Celery Tasks](../tasks/celery-tasks.md) - Async delivery
- [Webhook Encryption](../deployment/security.md) - Secret encryption
