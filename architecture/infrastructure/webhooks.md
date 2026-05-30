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
    event_type = db.Column(db.String(32))  # post.published, post.unpublished, etc.
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

## Webhook Encryption (`app/webhook_encryption.py`)

AES-256-GCM encryption for webhook secrets at rest. Secrets are encrypted before storage and decrypted on demand via the `Webhook.secret` property.

### Configuration

Requires `WEBHOOK_ENCRYPTION_KEY` environment variable. Accepts either:
- A 64-character hex-encoded string (decoded to 32 bytes)
- A raw 32-byte string

### Functions

| Function | Purpose |
|----------|---------|
| `encrypt_webhook_secret(plaintext: str) -> str` | Encrypt secret, returns base64-encoded nonce + ciphertext + tag |
| `decrypt_webhook_secret(encrypted: str) -> str` | Decrypt base64-encoded encrypted secret |

### Encryption Details

- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Nonce**: 12 bytes, generated via `os.urandom()`
- **Key size**: 32 bytes
- **Output**: Base64-encoded concatenation of nonce + ciphertext + authentication tag
- **Error handling**: Raises `WebhookEncryptionError` on failure

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

## Delivery Architecture

Webhook delivery uses a two-level dispatch pattern:

1. **`deliver_webhook_task`** (`app/tasks.py:195`): Receives a `webhook_event_id`, queries all enabled webhooks matching the event type, and dispatches individual `deliver_single_webhook_task` invocations — one per webhook. This enables per-webhook retry without blocking other webhooks.

2. **`deliver_single_webhook_task`** (`app/tasks.py:231`): Handles delivery to a single webhook endpoint with independent retry logic (up to 3 retries with exponential backoff). Responsibilities:
   - SSRF validation via `is_safe_webhook_url()`
   - HMAC-SHA256 signature generation and header injection
   - HTTP POST with `allow_redirects=False`
   - Retry on HTTP errors (>=400) or request exceptions
   - Delivery status tracking via `_update_delivery_status()`

```
create_webhook_event()
  └─► deliver_webhook_task (per event)
        ├─► deliver_single_webhook_task (webhook A)
        ├─► deliver_single_webhook_task (webhook B)
        └─► deliver_single_webhook_task (webhook C)
```

The deprecated `deliver_webhook()` synchronous function is retained for backward compatibility but should not be used for new code.

## SSRF Protection

The `is_safe_webhook_url()` utility in `app/utils.py:383-485` performs extensive validation:

- **Scheme check**: Only `http://` and `https://` allowed
- **Hostname required**: Rejects URLs without a hostname
- **Userinfo blocking**: Rejects URLs containing username/password (e.g., `http://user:pass@host`)
- **Loopback hostname blocking**: Blocks `127.0.0.1`, `::1`, `localhost`, `0.0.0.0`
- **DNS resolution**: Resolves hostname to all address families (IPv4 + IPv6) via `socket.getaddrinfo`
- **Per-IP validation** (each resolved IP must pass all checks):
  - **Loopback**: `ip.is_loopback` (127.0.0.0/8, ::1)
  - **Private**: `ip.is_private` (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  - **Link-local**: `ip.is_link_local` (169.254.0.0/16, fe80::/10)
  - **Reserved**: `ip.is_reserved`
  - **Multicast**: `ip.is_multicast`
  - **IPv4-mapped IPv6**: Checks `::ffff:` prefix and blocks mapped private/loopback IPs
  - **Cloud metadata endpoints**:
    - AWS: `169.254.169.254` (hardcoded check)
    - GCP: `metadata.google.internal` (hardcoded check)
  - **Global routability**: `ip.is_global` check — must be publicly routable
- **Return value**: `tuple[bool, str]` — `(True, "URL is safe")` or `(False, "<reason>")`
- **Redirect blocking**: Both `deliver_webhook()` and `deliver_webhook_task` set `allow_redirects=False`

### DNS Time-of-Check Gap

`is_safe_webhook_url()` resolves the hostname's DNS once and validates the returned IP addresses. There is no mechanism to hold the resolved IP locked for the duration of the HTTP request. This creates a **DNS rebinding vulnerability window**: between the DNS resolution in `is_safe_webhook_url()` and the actual HTTP request, the DNS record could change to point to a private/internal IP address (e.g., via a short TTL or attacker-controlled DNS server).

**Impact:** A webhook URL that appears safe at validation time (e.g., `https://attacker-controlled-domain.com/webhook`) could resolve to a private IP address when the actual request is made, potentially enabling SSRF attacks against internal services.

**Limitations:**
- No lock or lease holds the resolved IP beyond the validation call
- Short TTL DNS records increase the window of vulnerability
- No binding of the validated IP to the request itself

**Mitigations to consider:** Pin the resolved IP and reuse it for the connection, use a DNS resolver that validates against the private IP check at request time, or employ a DNS-over-HTTPS provider that caches and re-validates records.

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
| `post.unpublished` | Post goes from published to draft |
| `subscriber.confirmed` | New subscriber confirms |

## Queue Reference

Webhook delivery uses the `webhooks` Celery queue (see `app/tasks.py:194`).

Other queues used by the system:

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:30` |
| `newsletter` | Newsletter delivery | `app/tasks.py:129` |
| `webhooks` | Webhook delivery | `app/tasks.py:194` |
| `email` | Transactional email | `app/tasks.py:333,354` |
| `backup` | Backup tasks | `app/tasks.py:375` |

## See Also
- [Celery Tasks](../tasks/celery-tasks.md) - Async delivery
- [Webhook Encryption](../deployment/security.md) - Secret encryption
