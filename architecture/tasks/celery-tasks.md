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

**Non-Retry Behavior:** On failure, returns `False` without raising an exception or calling `self.retry()`. Variant generation is non-critical (falls back to original image), so failures are logged but do not trigger Celery retry. This prevents unnecessary retry attempts for non-essential image processing.

### `send_newsletter_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True,
             time_limit=600, soft_time_limit=540, queue='newsletter')
def send_newsletter_task(self: Any, post_ids: List[int]) -> bool:
```

Sends newsletter to all confirmed subscribers (manual/ad-hoc sends from admin dashboard — the daily scheduled newsletter uses `send_daily_newsletter` in `app/scheduler.py` instead):
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

Dispatches webhook deliveries to individual endpoints:
1. Fetches event and enabled webhooks for the event type
2. Dispatches each webhook to `deliver_single_webhook_task` for per-webhook delivery
3. Marks event as delivered (individual webhooks update delivery status)

### `deliver_single_webhook_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='webhooks')
def deliver_single_webhook_task(self, webhook_event_id: int, webhook_id: int) -> bool:
```

Delivers a webhook event to a single endpoint with per-webhook retry:
1. SSRF protection via `is_safe_webhook_url()` URL validation
2. HMAC-SHA256 payload signing via `sign_webhook_payload()`
3. `requests.post()` with `WEBHOOK_TIMEOUT` and `allow_redirects=False`
4. On HTTP success: calls `_update_delivery_status()` to update delivery status
5. On HTTP error or request exception: calls `self.retry(exc=e)` with exponential backoff
6. After max retries: logs error and calls `_update_delivery_status()` to mark failed

### `deliver_single_webhook_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='webhooks')
def deliver_single_webhook_task(self, webhook_event_id: int, webhook_id: int) -> bool:
```

Delivers a webhook event to a single endpoint with per-webhook retry. Called by `deliver_webhook_task` which dispatches individual deliveries for each registered webhook (line 223).

Features:
- **SSRF Protection**: URL validation via `is_safe_webhook_url()` before request
- **HMAC Signing**: `X-Webhook-Signature` header via `sign_webhook_payload()`
- **Retry Logic**: Calls `self.retry(exc=e)` on HTTP errors and request exceptions
- **Delivery Status**: Updates `WebhookEvent.delivery_status` via `_update_delivery_status()`

**Non-Retry Behavior:** On `MaxRetriesExceededError`, delivery is marked as failed via `_update_delivery_status()` without further retries (line 299-301).

**Dispatch Pattern:**
```
deliver_webhook_task (event-level)
  └── deliver_single_webhook_task (per-webhook, called for each enabled webhook)
```

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

Runs database backup asynchronously via `create_backup()`:
- Uses `compress=True`
- Uses `keep=7`
- Uses `encrypt=False`
- Creates `blog_YYYYMMDD_HHMMSS.db.gz` files (compressed, unencrypted)

**Non-Retry Behavior:** On failure, returns `False` without raising an exception or calling `self.retry()`. Backup failures are logged but do not trigger Celery retry, as the scheduler will attempt the next scheduled backup.

## Error Handling

| Task | Failure Behavior | Retry |
|------|------------------|-------|
| `generate_image_variants` | Returns `False` | No |
| `send_newsletter_task` | Exception triggers `self.retry(exc=e)` | Yes |
| `deliver_webhook_task` | Dispatches to `deliver_single_webhook_task` per webhook | N/A (dispatch only) |
| `deliver_single_webhook_task` | Exception triggers `self.retry(exc=e)`; after max retries logs error and updates status | Yes |
| `send_confirmation_task` | Exception triggers `self.retry(exc=e)` | Yes |
| `send_password_reset_task` | Exception triggers `self.retry(exc=e)` | Yes |
| `run_backup_task` | Returns `False` | No |

**Note:** `deliver_webhook_task` is a dispatcher that delegates to `deliver_single_webhook_task` for each webhook. The per-webhook task has independent retry logic — it calls `self.retry(exc=e)` on HTTP errors or request failures, with exponential backoff up to `max_retries=3`.

## Retry Policy

- `max_retries=3` (2 for backup)
- `retry_backoff=True` (exponential backoff)
- Time limits for long-running tasks

## Database Session Management

All Celery tasks that interact with the database should use `db.session.remove()` in a `finally` block to clean up the scoped session after task completion. This pattern is used throughout `app/tasks.py`:

```python
try:
    # Database operations
    ...
    db.session.commit()
finally:
    db.session.remove()
```

This ensures that:
- The scoped session is properly closed after each task
- Database connections are returned to the pool
- No stale connections are left hanging

Tasks using this pattern: `send_newsletter_task`, `deliver_webhook_task`, `deliver_single_webhook_task`, `send_confirmation_task`, `send_password_reset_task`, `run_backup_task`.

## See Also
- [APScheduler](tasks/scheduler.md) - In-process scheduled jobs
- [Email Infrastructure](../infrastructure/email.md) - Email sending
- [Webhooks Infrastructure](../infrastructure/webhooks.md) - Webhook delivery
