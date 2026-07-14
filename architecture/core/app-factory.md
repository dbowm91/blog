# Core Application

## App Factory (`app/__init__.py`)

The `create_app()` function is the main entry point for initializing the Flask application. It performs the following initialization steps:

### 1. Configuration Validation
- Validates `SECRET_KEY` is set and at least 32 characters
- Validates `ADMIN_PASSWORD` is set
- Validates full configuration via `_validate_config()`

### 2. Flask App Setup
```python
app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = ...
app.config["SQLALCHEMY_DATABASE_URI"] = ...  # SQLite default
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE", "true"
).lower() in ("true", "1", "yes")  # Defaults to "true" string, raises error if explicitly False in production
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE + 1MB
```

### 3. Extensions Initialized
| Extension | Purpose |
|-----------|---------|
| `SQLAlchemy` | Database ORM |
| `Flask-Login` | User authentication |
| `Flask-Migrate` | Database migrations |
| `Flask-Caching` | Response/data caching |
| `Flask-Limiter` | Rate limiting |
| `Flask-Compress` | Gzip compression |

### 4. Blueprints Registered
| Blueprint | Prefix | Purpose |
|----------|--------|---------|
| `public` | `/` | Public blog pages |
| `admin` | `/admin` | Admin dashboard |
| `rss` | (none) | RSS/Atom/JSON feeds at root level (`/rss`, `/atom`, `/json`) |
| `errors` | - | Error handlers |
| `api` | `/api` | REST API |
| `swaggerui` | `/api/docs` | API documentation |

### 5. Middleware & Hooks

**Before Request:**
- Generate request ID (`g.request_id`)
- Generate CSP nonce (`g.csp_nonce`)
- CSRF validation for POST requests: sliding window of 5 valid tokens per session (app/csrf.py:20), token rotation on validation (app/csrf.py:53-60), and global enforcement via before_request_handler() (app/__init__.py:296-298)
- Session timeout check with sliding expiration

**After Request:**
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- CSP headers with nonce
- HSTS in production
- Prometheus metrics collection

### 6. SQLite Pragmas

SQLite pragmas are set via SQLAlchemy event listener (not static PRAGMA statements):

```python
@event.listens_for(db.engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
```

### 7. Database Initialization
- Auto-create first admin user if none exists
- Initialize `SiteSettings` if none exist
- Initialize FTS5 search tables
- Run integrity check (`PRAGMA integrity_check` for SQLite; skipped for non-SQLite dialects)

**FTS Initialization Note:** FTS init failures are caught and rolled back silently (`app/__init__.py:430-433`). The user is never informed if search functionality is unavailable. Consider surfacing a user-visible error when FTS init fails rather than failing silently.

### 8. Background Services
- APScheduler initialization
- Page view buffer initialization

**Page View Buffer (`app/page_view_buffer.py`):** Configured via `PAGE_VIEW_BUFFER_SIZE` env var (default: disabled, value `0`). When enabled (`> 0`), page views are batched in memory and flushed to the database periodically, reducing per-request write load.

#### Daemon Thread Mechanics

- `PageViewBuffer` spawns a **daemon thread** (`threading.Thread(..., daemon=True)`) that runs `_flush_loop()`.
- The loop uses `threading.Event.wait(timeout=flush_interval)` to sleep between flushes, checking `_stop_event` each iteration.
- Flush triggers:
  1. When the internal `Queue` reaches `PAGE_VIEW_BUFFER_SIZE` (checked synchronously after each `record()` call)
  2. Every `PAGE_VIEW_FLUSH_INTERVAL` seconds (default: 5, configurable via env var)
  3. On application shutdown — `stop()` sets the event, joins the thread with a 10s timeout, then performs a final `_flush_now()`

#### Thread Safety

- `_flush_lock` (`threading.Lock`) serializes concurrent flush attempts — only one thread can drain the queue and write to the database at a time.
- `_buffer_lock` (`threading.Lock`) protects singleton initialization in `init_page_view_buffer()`.
- The `Queue` itself is thread-safe for `put()`/`get_nowait()` operations.

#### Flush Behavior

- `_flush_now()` drains all pending items from the `Queue` into a list, then performs a **single bulk insert** via `db.session.execute(PageView.__table__.insert(), [...])`.
- On success, `flushed` stat is incremented and views are committed.
- On `SQLAlchemyError` or `OSError`, the session is rolled back, views are counted as `dropped`, and an error is logged. Individual view losses do not crash the application.

#### Fallback Mode

When `PAGE_VIEW_BUFFER_SIZE <= 0`, `init_page_view_buffer()` returns `None` and `record_page_view()` falls back to **synchronous inserts** — each page view is written directly to the database in the request path.

#### Lifecycle Integration

- `init_page_view_buffer(db, PageView)` is called during app factory background services initialization (`app/__init__.py`).
- `shutdown_page_view_buffer()` is called during graceful shutdown to flush remaining views.
- `get_buffer()` returns the global singleton (or `None` if disabled).

**Tag Cache:** Tag counts are cached via `flask-caching` with configurable TTL (`TAG_CACHE_TTL_SECONDS`). The `_get_tag_counts()` function in `app/tag_cache.py` uses `@cache.memoize()` for request-context queries and falls back to uncached queries for non-request contexts (e.g., CLI). Cache is invalidated via `invalidate_tag_cache()` after tag-modifying operations.

**Footer Exclusion:** The `inject_footer_data()` context processor (`app/context_processors.py:158-178`) returns empty footer data for `/admin`, `/api`, and `/rss` paths, avoiding unnecessary database queries for pages that don't render the public footer.

### 9. CLI Commands

Registered via `register_cli_commands()` in `app/cli.py`:

| Command | Description |
|---------|-------------|
| `flask rebuild-search` | Rebuild the FTS5 search index |
| `flask cleanup-orphaned-images` | Remove image files not associated with any post |
| `flask create-admin` | Create a new admin user (interactive prompt) |
| `flask promote-admin <username>` | Promote an existing user to admin (non-interactive) |
| `flask check-integrity` | Run `PRAGMA integrity_check` on the database |
| `flask export-data <output_file>` | Export posts, subscribers, tags, and pages as JSON |
| `flask import-data <input_file>` | Import posts, subscribers, tags, and pages from JSON |
| `flask seed` | Generate sample data (options: `--posts`, `--subscribers`, `--published/--draft` (boolean flag pair, app/cli.py:264-268)) |

### 10. Vite Integration

Initialized via `init_vite(app)` in `app/vite.py`:

- Registers `vite_asset()` as a Jinja2 global function for content-hashed asset URLs
- Reads `.vite/manifest.json` to resolve hashed filenames in production
- Falls back to MD5 content-hash query strings for CSS/non-JS assets
- Respects `CDN_URL` config for asset path prefixing

### 11. Structured Logging

Configured via `configure_logging(app)`:

- **Formatter**: `StructuredLogFormatter` outputs JSON logs with `timestamp`, `level`, `request_id`, `message`
- **Filter**: `RequestIdFilter` injects `g.request_id` into log records
- **Handler**: `RotatingFileHandler` writes to `logs/blog.log` (10MB max, 10 backups)
- **Level**: INFO in production; debug/testing modes skip file handler

### 12. ProxyFix Middleware

```python
proxy_count = int(os.environ.get("PROXY_COUNT", 1))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=1, x_host=1)
```

`PROXY_COUNT` controls trusted proxy hops (default: 1). Required behind reverse proxies like nginx.

### 13. Cache Configuration

| Environment | Backend | Config |
|-------------|---------|--------|
| Production (`FLASK_ENV=production`) | `RedisCache` | `CACHE_REDIS_URL` (default: `redis://localhost:6379/0`), prefix `blog_`, 300s TTL |
| Development | `SimpleCache` | 300s TTL |

Cache is initialized via `flask-caching`. Rate limiting uses separate `RATE_LIMIT_STORAGE_URI` config.

### 14. Security Headers (CSP)
```
Content-Security-Policy:
  default-src 'self';
  style-src 'self' 'nonce-{nonce}';
  style-src-attr 'unsafe-inline';
  font-src 'self';
  img-src 'self' data:;
  script-src 'self' 'nonce-{nonce}';
  connect-src 'self';
  frame-src 'none';
  frame-ancestors 'none'
```

**Note:** `style-src-attr 'unsafe-inline'` is required for the theme system's inline CSS variables and dynamic styling.

## Configuration (`app/config.py`)

Configuration is loaded from `config.toml` with environment variable overrides.

### Priority (highest to lowest)
1. Environment variables
2. `config.toml` file
3. Default values in `app/config.py`

### Key Configuration Categories

| Category | Settings |
|----------|----------|
| **App** | `SECRET_KEY`, `POSTS_PER_PAGE`, `SESSION_LIFETIME_HOURS` |
| **Admin** | `ADMIN_USERNAME`, `ADMIN_PASSWORD` |
| **Server** | `SERVER_HOST`, `SERVER_PORT`, `DEBUG` |
| **Author** | `AUTHOR_NAME`, `AUTHOR_ROLE`, `AUTHOR_AVATAR` |
| **Site** | `BASE_URL`, `CDN_URL`, `RELATED_POSTS_COUNT` |
| **Email** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| **Newsletter** | `NEWSLETTER_SEND_TIME`, `CONFIRMATION_EXPIRY_HOURS` |

## Extensions (`app/extensions.py`)

```python
db = SQLAlchemy()           # Database ORM
login_manager = LoginManager()  # User authentication
login_manager.login_view = "admin.login"
login_manager.session_protection = "strong"
migrate = Migrate()         # Database migrations
```

## Context Processors (`app/context_processors.py`)

Provides template variables for all templates:
- `csrf_token`, `csp_nonce` - CSRF token and CSP nonce (from `inject_csrf()`)
- `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url` - Site configuration (from `inject_config()`)
- `theme_preset`, `theme_vars`, `syntax_theme`, `custom_css_enabled`, `custom_css`, `logo_text`, `theme_presets` - Theme settings via centralized `ThemeService` (Phases 02–07 complete). Provides Halloy TOML parsing, `BlogTheme` translation, registry resolution, caching, and dark/light CSS variable emission. `ThemeService` is the sole runtime palette source; legacy `THEME_PRESETS` dict retained but no longer authoritative.
- `recent_posts_footer`, `recent_posts_sidebar`, `footer_tags`, `footer_tag_counts` - Footer data (from `inject_footer_data()`)
- `show_footer_posts` - Boolean controlling footer post display (from `inject_show_footer_posts()`)

## See Also
- [Models](core/models.md) - Database models
- [Configuration](core/configuration.md) - Detailed configuration
- [Routes: API](../routes/api-routes.md) - REST API endpoints
- [Routes: Admin](../routes/admin-routes.md) - Admin dashboard routes
- [Routes: Public](../routes/public-routes.md) - Public blog routes
