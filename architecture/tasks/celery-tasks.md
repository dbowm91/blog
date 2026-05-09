# Celery Tasks (`app/tasks.py`)

Async task queue using Celery with Redis as broker.

## Queues

| Queue | Purpose |
|-------|---------|
| `images` | Image processing |
| `newsletter` | Newsletter delivery |
| `webhooks` | Webhook delivery |
| `email` | Transactional emails |
| `backup` | Database backups |

## Task Definitions

### `generate_image_variants`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='images')
def generate_image_variants(self, filename: str) -> bool:
```

Generates responsive image variants:
- 400w WebP and original format
- 800w WebP and original format
- 1200w WebP and original format

**Storage Support:** Local and S3 backends

### `send_newsletter_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True,
             time_limit=600, soft_time_limit=540, queue='newsletter')
def send_newsletter_task(self: Any, post_ids: List[int]) -> bool:
```

Sends newsletter to all confirmed subscribers:
1. Fetches posts by IDs
2. Counts confirmed subscribers
3. Renders newsletter HTML/text
4. Sends via SMTP with retry logic
5. Updates `newsletter_sent_at` on success

### `deliver_webhook_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='webhooks')
def deliver_webhook_task(self, webhook_event_id: int) -> bool:
```

Delivers webhook events:
- SSRF protection via URL validation
- HMAC-SHA256 payload signing
- Exponential backoff retry
- Marks event delivered on success

### `send_confirmation_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='email')
def send_confirmation_task(self, subscriber_id: int) -> bool:
```

Sends confirmation email to new subscriber.

### `send_password_reset_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='email')
def send_password_reset_task(self, user_id: int, token: str) -> bool:
```

Sends password reset email to user.

### `run_backup_task`

```python
@shared_task(bind=True, max_retries=2, retry_backoff=True, queue='backup')
def run_backup_task(self) -> bool:
```

Runs database backup asynchronously.

## Retry Policy

- `max_retries=3` (2 for backup)
- `retry_backoff=True` (exponential backoff)
- Time limits for long-running tasks

## See Also
- [APScheduler](tasks/scheduler.md) - In-process scheduled jobs
- [Email Infrastructure](../infrastructure/email.md) - Email sending
- [Webhooks Infrastructure](../infrastructure/webhooks.md) - Webhook delivery
