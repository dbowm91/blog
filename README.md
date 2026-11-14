# DevLog

DevLog is a self-hosted blog for technical writing. Write Markdown posts and pages, manage comments and subscribers, publish newsletters, and use a themed admin dashboard. SQLite is the default database. SMTP and Redis are optional integrations.

[![CI](https://github.com/dbowm91/blog/actions/workflows/ci.yml/badge.svg)](https://github.com/dbowm91/blog/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Quick start

### Docker

Install Docker Compose, then clone the repository and copy the environment template:

```bash
git clone https://github.com/dbowm91/blog.git
cd blog
cp .env.example .env
```

Edit `.env` and set strong values for `SECRET_KEY` and `ADMIN_PASSWORD`. For Docker Compose, set `REDIS_URL=redis://redis:6379/0`. For a public deployment, also set `BASE_URL` to the URL readers will use, such as `https://blog.example.com`.

Build the images, create the initial configuration and administrator, then start DevLog:

```bash
docker compose --profile production build
docker compose --profile production run --rm blog \
  devlog onboard run --mode docker --profile docker-production
docker compose --profile production up -d
```

Open <http://localhost:5000/admin/login>. The app listens on `127.0.0.1`, so put a TLS-enabled reverse proxy in front of it before making it public. Scheduled publishing, newsletters, and other scheduled jobs are disabled by default. To enable them, set `ENABLE_SCHEDULER=true` on exactly one app container.

### Native system install

On Linux, install the verified release, create the service account, then run onboarding:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | sudo bash -s -- --native --system
sudo useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin devlog
sudo devlog onboard run --mode native --scope system --profile native-production
```

Skip `useradd` if the `devlog` account already exists. For a user-scoped install, upgrade options, or Docker installation from a release, see the [installation guide](docs/installation.md).

### Local development

```bash
git clone https://github.com/dbowm91/blog.git
cd blog
./scripts/setup-dev.sh
FLASK_APP=run:app venv/bin/python -m flask create-admin
venv/bin/python run.py
```

The setup script creates a virtual environment, generates local credentials, installs dependencies, and applies database migrations. The `create-admin` command prompts for the first admin account. Then open <http://localhost:5000/admin/login>.

For plain HTTP testing, set both `DEBUG=true` and `SESSION_COOKIE_SECURE=false` in `.env`. Debug mode enables the Werkzeug debugger, so use it only on a local machine and do not expose the server publicly.

## What DevLog includes

- Markdown posts and pages, tags, series, drafts, scheduled publishing, and revisions
- Full-text search, threaded comments, RSS, Atom, and JSON Feed
- Newsletter management, subscriber tools, webhooks, and a categorized media library
- Halloy themes, locally hosted fonts, and page backdrops
- A standalone `devlog` CLI, encrypted backups, health checks, and optional metrics
- Admin accounts with two-factor authentication, audit history, and session controls

## Configuration

Set secrets in environment variables or `.env`. Use `config.toml` for site and service settings. Environment variables take precedence over `config.toml`, and built-in defaults apply when neither provides a value. See [`config.toml.example`](config.toml.example) for the available settings and the [installation guide](docs/installation.md) for configuration details.

## Documentation

- [User guide](USAGE.md): day-to-day writing and administration
- [Installation guide](docs/installation.md): native, Docker, development, onboarding, and configuration
- [Deployment guide](DEPLOY.md): production deployment and operations
- [API reference](docs/api/posts.md) and [interactive API docs](http://localhost:5000/api/docs)
- [Theme operator guide](docs/themes/operator-guide.md)
- [Documentation index](docs/index.md)
- [Contributing](CONTRIBUTING.md) and [security policy](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
