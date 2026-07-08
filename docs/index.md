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

- [Architecture](../ARCHITECTURE.md) - System design and data flow
- [Deployment](https://github.com/sugarwookie/blog/blob/master/DEPLOY.md) - Production deployment guide
- [API Documentation](https://github.com/sugarwookie/blog/blob/master/docs/openapi.yaml) - OpenAPI specification

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