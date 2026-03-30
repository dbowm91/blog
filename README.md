# DevLog

A personal blog platform built with Flask, featuring an admin dashboard, newsletter, RSS feed, and analytics.

## Features

- **Blog posts** — Markdown editor with image uploads, tags, and SEO-friendly slugs
- **Admin dashboard** — Create, edit, delete posts with page view and share analytics
- **Newsletter** — Email subscriptions with confirmation and daily digest (scheduler starts automatically)
- **RSS feed** — Auto-generated feed at `/rss`
- **Search** — Full-text search across posts
- **Rate limiting** — Login and API endpoint protection
- **Security** — CSRF protection, security headers, password hashing

## Requirements

- Python 3.14+
- SQLite

## Setup

### Quick Start

```bash
./setup.sh
```

This will:
- Check Python version (3.14+ required)
- Create a virtual environment
- Install production dependencies
- Generate `.env` with random `SECRET_KEY` and `ADMIN_PASSWORD`
- Create required directories (`instance/`, `logs/`, `static/uploads/`)

For development (includes pytest):

```bash
./setup.sh --dev
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ADMIN_PASSWORD` | Yes | Admin login password |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_USER` | No | SMTP username for newsletter emails |
| `SMTP_PASSWORD` | No | SMTP password for newsletter emails |

> **First run**: The admin user is auto-created on startup using `ADMIN_USERNAME` and `ADMIN_PASSWORD`. The SQLite database is created in `instance/blog.db`.

> **Production**: Use a unique, random `SECRET_KEY`. Never reuse the development key in production.

### Configuration

Edit `config.toml` for site settings:

```toml
[app]
title = "DevLog"
description = "A place for thoughts on code..."
posts_per_page = 10

[author]
name = "Your Name"
role = "Your Role"

[site]
base_url = "http://localhost:5000"
```

## Running

### Development

```bash
# Set environment variables
export SECRET_KEY="your-secret-key"
export ADMIN_PASSWORD="your-password"

# Run with Flask dev server
python run.py
```

Visit `http://localhost:5000`. Admin at `http://localhost:5000/admin/`.

### Production (Granian)

[Granian](https://github.com/emmett-framework/granian) is a Rust-based Python server supporting HTTP/1, HTTP/2, and WebSockets.

```bash
# Install Granian
pip install granian

# ASGI mode (recommended)
granian --interface asgi --host 0.0.0.0 --port 5000 run:asgi_app

# WSGI mode
granian --interface wsgi --host 0.0.0.0 --port 5000 run:app
```

#### ASGI vs WSGI

This app exports both `app` (WSGI) and `asgi_app` (ASGI) from `run.py`:

- **ASGI** (`run:asgi_app`) — Uses `asgiref.WsgiToAsgi` adapter. Supports HTTP/2 natively. Recommended for Granian.
- **WSGI** (`run:app`) — Traditional sync interface. Works with Gunicorn, uWSGI, Granian.

Both modes use the same Flask codebase. The ASGI wrapper is a thin adapter that passes requests through to Flask's WSGI layer.

#### Granian Options

```bash
granian --interface asgi \
    --host 0.0.0.0 \
    --port 5000 \
    --workers 4 \
    --http auto \
    run:asgi_app
```

| Option | Description | Default |
|--------|-------------|---------|
| `--interface` | `asgi`, `wsgi`, or `rsgi` | `rsgi` |
| `--host` | Bind address | `127.0.0.1` |
| `--port` | Bind port | `8000` |
| `--workers` | Worker processes | `1` |
| `--http` | HTTP version (`1`, `2`, `auto`) | `auto` |

### Production (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## Testing

```bash
# Run all tests
ADMIN_PASSWORD=test SECRET_KEY=test python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_public.py -v
```

## Project Structure

```
blog/
├── app/
│   ├── __init__.py          # App factory, middleware, logging
│   ├── config.py            # Configuration from TOML + env vars
│   ├── models.py            # SQLAlchemy models
│   ├── extensions.py        # Flask extensions (db, login, migrate)
│   ├── csrf.py              # CSRF token generation/validation
│   ├── email.py             # SMTP email sending
│   ├── utils.py             # Slug generation, XML escaping
│   ├── base62.py            # Short URL encoding
│   ├── scheduler.py         # Newsletter cron job
│   ├── routes/
│   │   ├── public.py        # Public routes (posts, search, RSS)
│   │   ├── admin.py         # Admin routes (dashboard, editor)
│   │   └── rss.py           # RSS feed generation
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, images, uploads
├── migrations/              # Alembic database migrations
├── tests/                   # pytest test suite
├── instance/                # SQLite database (auto-created, gitignored)
├── logs/                    # Application logs (auto-created, gitignored)
├── config.toml              # Site configuration
├── requirements.txt         # Python dependencies
├── run.py                   # Entry point (WSGI + ASGI)
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── AGENTS.md                # Agent coding guidelines
└── README.md                # This file
```

## Routes

### Public

| Route | Description |
|-------|-------------|
| `GET /` | Homepage with paginated posts |
| `GET /post/<slug>` | Individual post |
| `GET /tag/<slug>` | Posts by tag |
| `GET /search?q=<query>` | Search posts |
| `GET /rss` | RSS feed |
| `GET /sitemap.xml` | XML sitemap |
| `GET /robots.txt` | Robots file |
| `POST /subscribe` | Newsletter subscription |
| `GET /confirm/<token>` | Confirm subscription |
| `GET /unsubscribe/<token>` | Unsubscribe |

### Admin

| Route | Description |
|-------|-------------|
| `GET /admin/login` | Login page |
| `POST /admin/login` | Authenticate |
| `GET /admin/` | Dashboard |
| `GET /admin/new` | New post form |
| `POST /admin/new` | Create post |
| `GET /admin/edit/<id>` | Edit post form |
| `POST /admin/edit/<id>` | Update post |
| `POST /admin/delete/<id>` | Delete post |
| `GET /admin/logout` | Logout |

## Database Migrations

```bash
# Initialize migrations (first time only)
flask db init

# Create migration after model changes
flask db migrate -m "description"

# Apply migrations
flask db upgrade
```

## Known Limitations

- **SQLite only** — No PostgreSQL/MySQL support configured
- **File uploads** — Stored locally in `static/uploads/`, no S3/cloud storage support
- **Newsletter scheduler** — Runs in-process via APScheduler; not suitable for multi-worker setups (file locking prevents duplicate sends on Unix)

## License

Private
