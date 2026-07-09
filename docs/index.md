# Welcome to DevLog

DevLog is a personal blog platform built with Flask, featuring an admin dashboard, newsletter scheduling, FTS5 full-text search, and more.

## Key Features

- **Admin Dashboard**: Full post/subscribers/media management with session tracking
- **Newsletter**: Scheduled sending with APScheduler
- **FTS5 Search**: Full-text search with SQLite, PostgreSQL migration path
- **Custom Theming**: CSS customization with sanitization
- **Security**: CSRF protection, TOTP 2FA, webhook encryption
- **API**: REST API for post/subscriber management

## Documentation

- [Architecture](../architecture/overview.md) - System design, data flow, and component relationships
- [Deployment](https://github.com/dbowm91/blog/blob/master/DEPLOY.md) - Production deployment guide
- [API Documentation](https://github.com/dbowm91/blog/blob/master/docs/openapi.yaml) - OpenAPI specification
- [Usage Guide](https://github.com/dbowm91/blog/blob/master/USAGE.md) - Detailed user guide for all admin features

### Architecture Deep Dives

- [App Factory & Configuration](../architecture/core/app-factory.md) - Flask app initialization
- [Data Models](../architecture/core/models.md) - 17 SQLAlchemy models
- [Routes](../architecture/routes/admin-routes.md) - Admin, public, API, and RSS routes
- [Services](../architecture/services/overview.md) - Business logic layer
- [Task Processing](../architecture/tasks/overview.md) - Celery and APScheduler
- [Infrastructure](../architecture/infrastructure/overview.md) - Search, email, storage, webhooks
- [Frontend](../architecture/frontend/overview.md) - Vite, templates, CSS
- [Testing](../architecture/testing/test-suite.md) - pytest, E2E, benchmarks
- [Security](../architecture/deployment/security.md) - 2FA, CSRF, rate limiting
- [Deployment](../architecture/deployment/docker.md) - Docker, CI/CD

## Quick Start

```bash
git clone https://github.com/dbowm91/blog.git
cd blog
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD=test-password-123
export SECRET_KEY=test-secret-key-test-secret-key-1234
python run.py
```

## License

MIT
