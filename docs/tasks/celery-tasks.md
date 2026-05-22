# Celery Tasks

## Task Queues

| Queue | Purpose |
|-------|---------|
| `images` | Image variant generation |
| `newsletter` | Newsletter delivery |
| `email` | Transactional emails (confirmation, password reset) |
| `webhooks` | Webhook delivery |
| `backup` | Database backups |

## Newsletter Task

### `send_newsletter_task`

Sends newsletter emails to confirmed subscribers.

**Configuration**: `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5)

The task increments `post.newsletter_attempts` on failure rather than using Celery's built-in retry mechanism. This provides:
- Predictable retry behavior across restarts
- Persistent retry state in the database
- No task duplication on worker crashes

**Important**: Email wrapper tasks (`send_confirmation_task`, `send_password_reset_task`) catch exceptions and return `False`, making `max_retries` ineffective. See [Email Wrapper Task Pattern](../infrastructure/email.md) for details.

### Newsletter Retry Configuration

`NEWSLETTER_MAX_RETRY_ATTEMPTS` defaults to 5 and can be configured in `config.toml`:

```toml
[newsletter]
max_retry_attempts = 5
```

When `post.newsletter_attempts >= NEWSLETTER_MAX_RETRY_ATTEMPTS`, the post is excluded from future newsletter runs and a warning is logged:

```
Newsletter: N posts excluded after M retry attempts: [id=X, title=Y, ...]
```

## Email Tasks

### `send_confirmation_task`

Wraps `send_confirmation()` for async execution. See [Email Wrapper Task Pattern](../infrastructure/email.md).

### `send_password_reset_task`

Wraps `send_password_reset()` for async execution. See [Email Wrapper Task Pattern](../infrastructure/email.md).

## Webhook Tasks

### `deliver_webhook_task`

Delivers webhook events to registered endpoints with:
- SSRF protection via URL validation
- HMAC signature (X-Webhook-Signature header)
- Configurable timeout (default: 10 seconds)
- Delivery status tracking (delivered, partial_failure, failed)

## Backup Tasks

### `run_backup_task`

Creates compressed database backups asynchronously. Runs with `max_retries=2`.

## Image Variant Generation

### `generate_image_variants`

Generates 400w, 800w, 1200w responsive variants in WebP format. Runs on the `images` queue.

## Testing Configuration

In test mode, Celery runs tasks eagerly (synchronously) via:

```python
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
```