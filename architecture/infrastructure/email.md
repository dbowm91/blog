# Email (`app/email.py`)

SMTP email delivery for newsletters and transactional emails.

## Email Types

| Type | Function | Purpose |
|------|----------|---------|
| Confirmation | `send_confirmation()` | Confirm subscriber email |
| Password Reset | `send_password_reset()` | Reset user password |
| Newsletter | `send_newsletter()` | Send newsletter to subscribers |

## SMTP Configuration

```python
SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587  # TLS
SMTP_USER = "user"
SMTP_PASSWORD = "password"
FROM_ADDRESS = "noreply@example.com"
SMTP_TIMEOUT = 30
```

## Core Functions

### `_send_email()`

```python
def _send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> None:
```

Low-level SMTP send with TLS.

### `_connect_smtp()`

Opens authenticated SMTP connection. Returns `None` on failure.

### `_send_email_with_retry()`

```python
def _send_email_with_retry(
    server: Optional[SMTP],
    from_address: str,
    to: str,
    msg_str: str,
    max_retries: int = 3
) -> tuple[bool, str, Optional[SMTP]]:
```

Sends with retry. Handles `SMTPServerDisconnected` by reconnecting.

### `send_newsletter()`

```python
def send_newsletter(
    posts: list[Any],
    subscribers: Any,
    total_subscribers: Optional[int] = None
) -> bool:
```

Bulk newsletter delivery:
1. Connects to SMTP
2. Pre-renders HTML and text templates
3. Iterates subscribers, replacing unsubscribe URL
4. Sends with retry
5. Logs progress every 50 emails

## Templates

Email templates in `app/templates/email/`:
- `base_email.html` - Base email template (standalone, not extending `base.html`)
- `confirm.html` - Subscription confirmation
- `password_reset.html` - Password reset
- `newsletter.html` - Newsletter layout

## Retry Logic

- `_send_email_with_retry()` default: **3 retries** (function parameter default, `app/email.py:111`)
- Newsletter override: **5 retries** (via the `NEWSLETTER_MAX_RETRY_ATTEMPTS` environment variable, default 5 in `app/config_legacy.py`)
- Reconnects on `SMTPServerDisconnected`

The retry architecture uses two distinct paths:
1. **Transactional emails** (confirmation, password reset): Use the default 3-retry count via `_send_email_with_retry()` called by Celery tasks. These are single-send operations where fewer retries are acceptable.
2. **Newsletter delivery**: Uses 5 retries via `NEWSLETTER_MAX_RETRY_ATTEMPTS` to handle transient SMTP failures across potentially thousands of recipients. The higher retry count reduces the chance of partial newsletter delivery due to temporary server issues.

## Queue Configuration

| Task | Queue | Purpose | Wrapper Pattern |
|------|-------|---------|-----------------|
| `send_newsletter_task` | `newsletter` | Bulk newsletter delivery | Calls synchronous `send_newsletter()` |
| `send_confirmation_task` | `email` | Subscriber confirmation emails | Calls synchronous `send_confirmation()` wrapper |
| `send_password_reset_task` | `email` | Password reset emails | Calls synchronous `send_password_reset()` wrapper |

**Wrapper Pattern:** `send_confirmation()` and `send_password_reset()` are synchronous functions that are called by their respective Celery tasks. This pattern allows the async task to handle retries and queue management while the wrapper function handles the actual SMTP delivery.
- [Celery Tasks](../tasks/celery-tasks.md) - Async email sending
- [Configuration](../core/configuration.md) - Email config
