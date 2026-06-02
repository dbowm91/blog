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

**Newsletter Three-Way Path:** The newsletter system has two delivery paths that both terminate at `email.send_newsletter()`:
1. **Daily scheduled:** `scheduler.send_daily_newsletter()` (APScheduler) → `email.send_newsletter()` (direct call)
2. **Manual/ad-hoc:** `send_newsletter_task` (Celery, this task) → `email.send_newsletter()` (admin dashboard triggers)

**Retry Gap:** This Celery task does NOT check `NEWSLETTER_MAX_RETRY_ATTEMPTS` (unlike the scheduler path at `app/scheduler.py:118`). The scheduler filters posts by `newsletter_attempts` to avoid retrying exhausted posts. This task sends for all requested post IDs regardless of attempt count — it is designed for manual/admin-triggered sends where the admin explicitly chooses which posts to send.

### `deliver_webhook_task`

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='webhooks')
def deliver_webhook_task(self, webhook_event_id: int) -> bool:
```

Dispatches webhook deliveries to individual endpoints:
1. Fetches event and enabled webhooks for the event type
2. Dispatches each webhook to `deliver_single_webhook_task` via `.delay()` (fire-and-forget)
3. Returns `True` immediately — parent success only means dispatch succeeded, not that individual webhooks were delivered

**Fire-and-forget pattern:** `deliver_webhook_task` uses `deliver_single_webhook_task.delay()` at `app/tasks.py:229`. The parent task returns success as soon as child tasks are enqueued. Each child runs independently with its own retry logic. A successful `deliver_webhook_task` return value does **not** indicate child delivery success — individual webhook outcomes are tracked via `_update_delivery_status()` on each `WebhookEvent`.

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

### `_update_delivery_status` (helper)

```python
def _update_delivery_status(event: Any, db: Any) -> None:
```

Determines the final `delivery_status` of a `WebhookEvent` after individual webhooks complete. Called by `deliver_single_webhook_task` after each webhook finishes (success, HTTP error, or exhausted retries).

**Logic (`app/tasks.py:318-347`):**
1. Count enabled webhooks for the event's `event_type`
2. If no enabled webhooks, set `delivery_status = None` and return
3. If `successful_deliveries + failed_deliveries < total_count`, not all webhooks have finished — return without updating
4. If all succeeded: `"delivered"`, `delivered = True`
5. If all failed: `"failed"`, `delivered = False`
6. Mixed results: `"partial_failure"`, `delivered = True`

**Concurrency dependency:** This function must run with `--concurrency=1` on the `webhooks` queue. Multiple concurrent workers calling `db.session.commit()` on the same event simultaneously could cause lost updates to the delivery counters. The single-worker constraint ensures sequential updates to `successful_deliveries` and `failed_deliveries`.

## Error Handling

| Task | Failure Behavior | Retry |
|------|------------------|-------|
| `generate_image_variants` | Returns `False` | No |
| `send_newsletter_task` | Returns `False` on send failure; Celery auto-retry only on uncaught exceptions | No (no explicit retry) |
| `deliver_webhook_task` | Dispatches to `deliver_single_webhook_task` per webhook | N/A (dispatch only) |
| `deliver_single_webhook_task` | Exception triggers `self.retry(exc=e)`; after max retries logs error and updates status | Yes |
| `send_confirmation_task` | Exception triggers `self.retry(exc=e)` | Yes |
| `send_password_reset_task` | Exception triggers `self.retry(exc=e)` | Yes |
| `run_backup_task` | Returns `False` | No |

**Note:** `deliver_webhook_task` is a dispatcher that delegates to `deliver_single_webhook_task` for each webhook. The per-webhook task has independent retry logic — it calls `self.retry(exc=e)` on HTTP errors or request failures, with exponential backoff up to `max_retries=3`.

## Global Celery Configuration

Global Celery settings are configured in `app/celery_app.py:20-31` via `celery_app.conf.update()`:

| Setting | Value | Purpose |
|---------|-------|---------|
| `task_serializer` | `json` | JSON serialization for tasks |
| `accept_content` | `['json']` | Only accept JSON payloads |
| `result_serializer` | `json` | JSON serialization for results |
| `timezone` | `UTC` | All timestamps in UTC |
| `enable_utc` | `True` | Use UTC for scheduling |
| `task_track_started` | `True` | Track task state transitions |
| `task_time_limit` | 300 | Hard kill after 5 minutes (default for all tasks) |
| `task_soft_time_limit` | 240 | Soft timeout raises `SoftTimeLimitExceeded` after 4 minutes |
| `worker_prefetch_multiplier` | `1` | Disable prefetching — one task at a time per worker |
| `worker_max_tasks_per_child` | 100 | Worker restarts after 100 tasks (prevents memory leaks) |

When Flask app context is available (`init_celery(app)` is called with an app):

| Setting | Value | Purpose |
|---------|-------|---------|
| `task_acks_late` | `True` | Acknowledge tasks after completion, not before |
| `task_reject_on_worker_lost` | `True` | Re-queue task if worker crashes |

**Task-specific overrides** (defined on individual tasks):
- `send_newsletter_task`: `time_limit=600`, `soft_time_limit=540` — longer limits for bulk email sending
- `run_backup_task`: `max_retries=2` (not 3)

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
- [APScheduler](scheduler.md) - In-process scheduled jobs
- [Email Infrastructure](../infrastructure/email.md) - Email sending
- [Webhooks Infrastructure](../infrastructure/webhooks.md) - Webhook delivery
