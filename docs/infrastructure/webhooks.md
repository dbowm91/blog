# Webhooks

Webhooks allow external services to receive notifications when events occur in the blog.

## Webhook Model

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `name` | string(100) | Webhook name |
| `url` | string(512) | Target URL for webhook delivery |
| `webhook_secret_encrypted` | LargeBinary(256) | Encrypted webhook secret (AES-256-GCM) |
| `event_type` | string(32) | Event type (e.g., `post.published`, `subscriber.confirmed`) |
| `enabled` | bool | Whether webhook is active |
| `created_at` | datetime | Creation timestamp |

### Secret Property

The `secret` property provides access to the decrypted webhook secret:

```python
@property
def secret(self) -> Optional[str]:
    """Get decrypted webhook secret."""
    if not self.webhook_secret_encrypted:
        return None
    from app.webhook_encryption import decrypt_webhook_secret
    try:
        return decrypt_webhook_secret(self.webhook_secret_encrypted.decode("utf-8"))
    except Exception:
        return None

@secret.setter
def secret(self, value: Optional[str]) -> None:
    """Encrypt and store webhook secret."""
    if not value:
        self.webhook_secret_encrypted = None
        return
    from app.webhook_encryption import encrypt_webhook_secret
    self.webhook_secret_encrypted = encrypt_webhook_secret(value).encode("utf-8")
```

## WebhookEvent Model

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `webhook_id` | int | Foreign key to Webhook |
| `event_type` | string(32) | Event type |
| `payload` | JSON | Event payload data |
| `target_id` | int | ID of the entity that triggered the event |
| `target_type` | string(32) | Type of entity (e.g., `post`, `subscriber`) |
| `delivered` | bool | Whether delivery was successful |
| `delivery_status` | string(32) | Delivery status: `delivered`, `partial_failure`, `failed` |
| `delivery_attempts` | int | Number of delivery attempts |
| `created_at` | datetime | Creation timestamp |

### Delivery Status Values

| Value | Description |
|-------|-------------|
| `delivered` | All webhooks succeeded |
| `partial_failure` | Some succeeded, some failed |
| `failed` | All failed |

## Event Types

- `post.published` - When a post is published
- `post.unpublished` - When a post is unpublished
- `subscriber.confirmed` - When a subscriber confirms their email

## Security

Webhook secrets are encrypted at rest using AES-256-GCM via `app/webhook_encryption.py`.