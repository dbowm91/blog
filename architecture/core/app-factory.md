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
app.config["SESSION_COOKIE_SECURE"] = True (in production)
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
| `rss` | `/rss`, `/atom`, `/json` | RSS/Atom/JSON feeds |
| `errors` | - | Error handlers |
| `api` | `/api` | REST API |
| `swaggerui` | `/api/docs` | API documentation |

### 5. Middleware & Hooks

**Before Request:**
- Generate request ID (`g.request_id`)
- Generate CSP nonce (`g.csp_nonce`)
- CSRF validation for POST requests
- Session timeout check with sliding expiration

**After Request:**
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- CSP headers with nonce
- HSTS in production
- Prometheus metrics collection

### 6. SQLite Pragmas
```python
PRAGMA journal_mode=WAL
PRAGMA busy_timeout=5000
```

### 7. Database Initialization
- Auto-create first admin user if none exists
- Initialize `SiteSettings` if none exist
- Initialize FTS5 search tables
- Run integrity check (`PRAGMA integrity_check`)

### 8. Background Services
- APScheduler initialization
- Page view buffer initialization

### 9. Security Headers (CSP)
```
Content-Security-Policy:
  default-src 'self';
  style-src 'self' 'nonce-{nonce}';
  font-src 'self';
  img-src 'self' data:;
  script-src 'self' 'nonce-{nonce}';
  connect-src 'self';
  frame-src 'none';
  frame-ancestors 'none'
```

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
- `site_settings` - Theme, syntax theme, custom CSS
- `tag_cache` - Cached tag counts
- `footer_data` - Recent posts, popular tags

## See Also
- [Models](core/models.md) - Database models
- [Configuration](core/configuration.md) - Detailed configuration
- [Routes Overview](../routes/overview.md) - All route blueprints
