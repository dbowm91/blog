# Configuration (`app/config.py`)

Configuration is centralized in `config.toml` with environment variable overrides.

## Configuration File: `config.toml`

### Structure

```toml
[app]
title = "DevLog"
description = "A developer's blog"
posts_per_page = 10
max_viewed_posts = 100
session_lifetime_hours = 24
session_ip_binding = "warn"
max_upload_size = 10485760  # 10MB
...

[admin]
username = "admin"

[server]
host = "0.0.0.0"
port = 5000
debug = false

[author]
name = "Author Name"
role = "Developer"

[site]
base_url = "http://localhost:5000"
related_posts_count = 3

[email]
smtp_host = "smtp.example.com"
smtp_port = 587
from_address = "noreply@example.com"

[newsletter]
send_time = "08:00"
confirmation_expiry_hours = 1

[search]
provider = "sqlite"  # or "postgresql"
config = {}
```

## Configuration Priority

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | Environment variable | `SECRET_KEY=abc123...` |
| 2 | config.toml | `posts_per_page = 10` |
| 3 | Default value | `SESSION_LIFETIME_HOURS = 24` |

## Key Settings

### Application Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `SECRET_KEY` | `SECRET_KEY` | **required** | Flask session key (min 32 chars) |
| `ADMIN_PASSWORD` | `ADMIN_PASSWORD` | **required** | Admin login password |
| `ADMIN_USERNAME` | `ADMIN_USERNAME` | `admin` | Admin username |
| `POSTS_PER_PAGE` | - | `10` | Posts per page (1-100) |
| `SESSION_LIFETIME_HOURS` | - | `24` | Session timeout |
| `SESSION_IP_BINDING` | - | `warn` | IP binding mode: `off`, `warn`, `enforce` |
| `MAX_UPLOAD_SIZE` | - | `10485760` | Max upload size in bytes |
| `MAX_VIEWED_POSTS` | - | `100` | Number of recent posts to track for "You've read" feature |
| `TAG_CACHE_TTL_SECONDS` | - | `60` | Cache TTL for tag counts |
| `DASHBOARD_PER_PAGE` | - | `20` | Posts per page in admin dashboard |
| `SUBSCRIBERS_PER_PAGE` | - | `50` | Subscribers per page in admin |
| `MEDIA_PER_PAGE` | - | `50` | Media items per page |
| `MEDIA_MAX_FILES` | - | `1000` | Maximum files in media library |
| `EXPORT_BATCH_SIZE` | - | `500` | Batch size for subscriber exports |
| `FTS_RESULT_LIMIT` | - | `100` | Maximum full-text search results |
| `PREVIEW_TOKEN_EXPIRY_DAYS` | - | `7` | Days until preview token expires |
| `HEALTH_CHECK_SECRET` | `HEALTH_CHECK_SECRET` | (empty) | Secret for health check endpoint |
| `DATA_BACKUP_DIR` | - | `backups` | Directory for backup files |
| `WEBHOOK_TIMEOUT` | - | `10` | Webhook delivery timeout (seconds) |
| `WEBHOOK_ENCRYPTION_KEY` | `WEBHOOK_ENCRYPTION_KEY` | (empty) | Key for webhook secret encryption |
| `COMPRESS_ALGORITHM` | - | `["zstd", "br", "gzip"]` | Supported compression algorithms |
| `SMTP_TIMEOUT` | - | `30` | SMTP connection timeout (seconds) |
| `SEARCH_PROVIDER` | - | `sqlite` | Search provider: `sqlite` or `postgresql` |
| `SEARCH_CONFIG` | - | `{}` | Search provider configuration |

### SESSION_IP_BINDING Modes

| Mode | Behavior |
|------|----------|
| `off` | No IP binding check. Sessions work from any IP address. |
| `warn` | Log a warning if IP address changes, but allow the request. |
| `enforce` | Invalidate the session and redirect to login if IP address changes. |

### Email Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `SMTP_HOST` | - | (from config) | SMTP server |
| `SMTP_PORT` | - | `587` | SMTP port |
| `SMTP_USER` | `SMTP_USER` | (empty) | SMTP username |
| `SMTP_PASSWORD` | `SMTP_PASSWORD` | (empty) | SMTP password |
| `FROM_ADDRESS` | - | (from config) | From email address |

### Newsletter Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `NEWSLETTER_SEND_TIME` | - | `08:00` | Daily send time (HH:MM) |
| `CONFIRMATION_EXPIRY_HOURS` | - | `1` | Subscriber confirmation deadline |
| `NEWSLETTER_MAX_RETRY_ATTEMPTS` | - | `5` | Max send retries |

### Storage Settings

Defined in `app/storage.py:53-60`, not in `app/config.py`.

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `STORAGE_BACKEND` | `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `S3_BUCKET` | `S3_BUCKET` | - | S3 bucket name |
| `S3_REGION` | `S3_REGION` | `us-east-1` | AWS region |
| `S3_ENDPOINT` | `S3_ENDPOINT` | - | S3-compatible endpoint |
| `S3_ACCESS_KEY` | `S3_ACCESS_KEY` | - | AWS access key |
| `S3_SECRET_KEY` | `S3_SECRET_KEY` | - | AWS secret key |
| `S3_PUBLIC_URL` | `S3_PUBLIC_URL` | - | Custom CDN URL |

### Redis/Cache Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `REDIS_URL` | `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `RATE_LIMIT_STORAGE_URI` | `RATE_LIMIT_STORAGE_URI` | `memory://` (dev) | Rate limit storage |
| `CACHE_REDIS_URL` | `CACHE_REDIS_URL` | `redis://localhost:6379/0` | Cache storage |

### Security Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `MAX_FAILED_ATTEMPTS` | - | `5` | Login attempts before lockout |
| `LOCKOUT_DURATION_MINUTES` | - | `15` | Account lockout duration |
| `LOGIN_FAILURE_DELAY` | `LOGIN_FAILURE_DELAY` | `0.05` | Delay on failed login (seconds, minimum 0.1s enforced (app/config.py:148 via max(LOGIN_FAILURE_DELAY, 0.1))) |
| `TOKEN_ENUMERATION_DELAY` | - | `0.1` | Delay to prevent token enumeration |

### Admin Rate Limits

`ADMIN_RATE_LIMITS` dict (app/config.py:165-172) defines per-endpoint rate limits as `(requests, seconds)` tuples:

| Key | Default | Description |
|-----|---------|-------------|
| `login` | `(5, 60)` | Login attempts per minute |
| `api_write` | `(100, 60)` | Write API calls per minute |
| `api_read` | `(500, 60)` | Read API calls per minute |
| `settings` | `(50, 60)` | Settings updates per minute |
| `post_create` | `(100, 60)` | Post creation per minute |
| `post_update` | `(100, 60)` | Post updates per minute |

### Comment Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `COMMENT_MIN_LENGTH` | - | `3` | Minimum comment length |
| `COMMENT_MAX_LENGTH` | - | `5000` | Maximum comment length |
| `COMMENT_RATE_LIMIT_PER_IP` | - | `5 per minute` | Rate limit per IP address |
| `COMMENT_RATE_LIMIT_PER_POST` | - | `3 per minute` | Rate limit per post |
| `COMMENT_NOTIFY_PENDING` | - | `false` | Notify admin of pending comments |
| `COMMENT_SPAM_WORDS` | - | (empty) | Comma-separated spam trigger words |

### Analytics Settings

| Variable | Env Var | Default | Description |
|----------|---------|---------|-------------|
| `ANALYTICS_DAYS_MIN` | - | `7` | Minimum days for analytics range |
| `ANALYTICS_DAYS_MAX` | - | `365` | Maximum days for analytics range |
| `PAGE_VIEW_BUFFER_SIZE` | `PAGE_VIEW_BUFFER_SIZE` | `0` | Buffer size for page view writes |

## Validation

The `_validate_config()` function validates:
- `send_time` is valid HH:MM format
- `posts_per_page` is 1-100
- `confirmation_expiry_hours` is positive integer
- `smtp_port` is 1-65535
- `base_url` has valid scheme and domain
- `dashboard_per_page` is positive integer (app/config.py:214-230)
- `subscribers_per_page` is positive integer (app/config.py:214-230)
- `media_per_page` is positive integer (app/config.py:214-230)
- `media_max_files` is positive integer (app/config.py:214-230)
- `max_upload_size` is positive integer (app/config.py:214-230)
- `export_batch_size` is positive integer (app/config.py:214-230)
- `fts_result_limit` is positive integer (app/config.py:214-230)
- `token_enumeration_delay` is positive number (app/config.py:232-241)
- `smtp_timeout` is positive integer (app/config.py:243-250)

## See Also
- [App Factory](core/app-factory.md) - How config is used
- [Email Infrastructure](../infrastructure/email.md) - Email configuration
- [Storage Infrastructure](../infrastructure/storage.md) - Storage backends
