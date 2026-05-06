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

Sends with exponential backoff retry. Handles `SMTPServerDisconnected` by reconnecting.

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
- `confirm.html` - Subscription confirmation
- `password_reset.html` - Password reset
- `newsletter.html` - Newsletter layout

## Retry Logic

- Max retries: 3 (configurable via `NEWSLETTER_MAX_RETRY_ATTEMPTS`)
- Exponential backoff
- Reconnects on `SMTPServerDisconnected`

## See Also
- [Celery Tasks](../tasks/celery-tasks.md) - Async email sending
- [Configuration](../core/configuration.md) - Email config
