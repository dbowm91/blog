# Configuration

## Application Settings

| Variable | Description |
|----------|-------------|
| `APP_TITLE` | Blog title |
| `APP_DESCRIPTION` | Blog description |
| `POSTS_PER_PAGE` | Number of posts per page |
| `SECRET_KEY` | Flask secret key |
| `MAX_VIEWED_POSTS` | Maximum viewed posts to track |
| `SESSION_LIFETIME_HOURS` | Session lifetime in hours |
| `SESSION_IP_BINDING` | Bind session to IP address |

## Admin Settings

| Variable | Description |
|----------|-------------|
| `ADMIN_USERNAME` | Admin username |
| `ADMIN_PASSWORD` | Admin password |

## Server Settings

| Variable | Description |
|----------|-------------|
| `SERVER_HOST` | Server host |
| `SERVER_PORT` | Server port |
| `DEBUG` | Debug mode |

---

## Missing Configuration Options

### PAGE_VIEW_BUFFER_SIZE

Page view buffering threshold. When greater than 0, page views are batched and written to the database periodically rather than immediately.

```python
PAGE_VIEW_BUFFER_SIZE = int(os.environ.get("PAGE_VIEW_BUFFER_SIZE", _config["app"].get("page_view_buffer_size", 0)))
```

Default: 0 (disabled)

---

### SEARCH_PROVIDER

Search provider selection. Currently supports "sqlite" for FTS5 or "postgresql" for future PostgreSQL support.

```python
SEARCH_PROVIDER = _config.get("search", {}).get("provider", "sqlite")
```

Default: "sqlite"

---

### SEARCH_CONFIG

Provider-specific search configuration. Structure depends on the search provider.

```python
SEARCH_CONFIG = _config.get("search", {}).get("config", {})
```

---

### DATA_BACKUP_DIR

Backup directory location for database backups.

```python
DATA_BACKUP_DIR = _config.get("backup", {}).get("data_backup_dir", "backups")
```

Default: "backups"

---

## Rate Limiting

### RATE_LIMIT_STORAGE_URI

Redis is only used when `FLASK_ENV=production`. In development, in-memory storage is used.

```python
RATE_LIMIT_STORAGE_URI = _env(
    "RATE_LIMIT_STORAGE_URI",
    "redis://localhost:6379/1" if os.environ.get("FLASK_ENV") == "production" else "memory://"
)
```

---

## Account Lockout

Failed login attempts are tracked with:

| Variable | Description |
|----------|-------------|
| `MAX_FAILED_ATTEMPTS` | Number of failed attempts before lockout (default: 5) |
| `LOCKOUT_DURATION_MINUTES` | Lockout duration in minutes (default: 15) |

From `app/config.py:142-143`:
```python
MAX_FAILED_ATTEMPTS = int(_config.get("security", {}).get("max_failed_attempts", 5))
LOCKOUT_DURATION_MINUTES = int(_config.get("security", {}).get("lockout_duration_minutes", 15))
```

---

### ADMIN_RATE_LIMITS

Rate limits for admin operations. Exceeding these limits results in HTTP 429 responses.

```python
ADMIN_RATE_LIMITS = {
    "login": (5, 60),       # 5 attempts per 60 seconds
    "api_write": (100, 60), # 100 writes per 60 seconds
    "api_read": (500, 60),  # 500 reads per 60 seconds
    "settings": (50, 60),   # 50 settings changes per 60 seconds
    "post_create": (100, 60),
    "post_update": (100, 60),
}
```

From `app/config.py:145-152`:
```python
ADMIN_RATE_LIMITS = {
    "login": (5, 60),
    "api_write": (100, 60),
    "api_read": (500, 60),
    "settings": (50, 60),
    "post_create": (100, 60),
    "post_update": (100, 60),
}
```