# Email Infrastructure

## Email Wrapper Task Pattern

The following Celery tasks wrap synchronous email functions and catch exceptions to prevent task retry storms:

### `send_confirmation_task`

Wraps `app.email.send_confirmation()` for sending subscriber confirmation emails.

```python
@shared_task(bind=True, retry_backoff=True, queue='email')
def send_confirmation_task(self: Any, subscriber_id: int) -> bool:
    try:
        subscriber = db.session.get(Subscriber, subscriber_id)
        if not subscriber:
            return False
        try:
            send_confirmation(subscriber)
            return True
        except Exception as e:
            current_app.logger.error(f"Confirmation email failed: {e}")
            return False  # Swallows exception - task will NOT retry
    finally:
        db.session.remove()
```

### `send_password_reset_task`

Wraps `app.email.send_password_reset()` for sending password reset emails.

```python
@shared_task(bind=True, retry_backoff=True, queue='email')
def send_password_reset_task(self: Any, user_id: int, token: str) -> bool:
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False
        try:
            send_password_reset(user, token)
            return True
        except Exception as e:
            current_app.logger.error(f"Password reset email failed: {e}")
            return False  # Swallows exception - task will NOT retry
    finally:
        db.session.remove()
```

## Email Task Retry Behavior

**Important**: Both tasks catch exceptions and return `False` instead of raising. This means:

- `max_retries=3` on the task is **ineffective** because exceptions are swallowed
- Tasks will NOT automatically retry on failure
- Failures are logged via `current_app.logger.error()`

This pattern prevents retry storms when email delivery is persistently failing (e.g., SMTP server unreachable).

## SMTP Configuration

Required environment variables:
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port (default: 587)
- `SMTP_USER`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP authentication password
- `FROM_ADDRESS`: Sender email address

## Email Queue

Email tasks run on the `email` Celery queue with `retry_backoff=True` for exponential backoff on infrastructure failures.