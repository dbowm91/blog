# Security Configuration

## Account Lockout

Failed login attempts are tracked to prevent brute-force attacks.

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FAILED_ATTEMPTS` | `5` | Number of failed attempts before lockout |
| `LOCKOUT_DURATION_MINUTES` | `15` | Lockout duration in minutes |

**Location:** `app/config.py:142-143`

```python
MAX_FAILED_ATTEMPTS = int(_config.get("security", {}).get("max_failed_attempts", 5))
LOCKOUT_DURATION_MINUTES = int(_config.get("security", {}).get("lockout_duration_minutes", 15))
```

## Rate Limiting

The application uses Flask-Limiter with configurable storage:

- **Production**: Redis storage for distributed rate limiting
- **Development**: In-memory storage

### RATE_LIMIT_STORAGE_URI

Redis is only used when `FLASK_ENV=production`. In development, in-memory storage is used.

```python
RATE_LIMIT_STORAGE_URI = _env(
    "RATE_LIMIT_STORAGE_URI",
    "redis://localhost:6379/1" if os.environ.get("FLASK_ENV") == "production" else "memory://"
)
```

## Admin Session Security

Admin sessions include:
- IP address binding
- User agent tracking
- Last activity timestamp
- Unique session ID

Session lifetime is configurable via `SESSION_LIFETIME_HOURS`.