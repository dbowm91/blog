# Installation

This guide covers first-time setup, configuration, and common operator tasks. For production deployment details, see the [deployment guide](../DEPLOY.md).

## Choose an installation method

| Method | Best for | Requirements |
|---|---|---|
| Native system | A Linux host running DevLog as a service | Python 3.12 or newer; elevated permissions for system paths |
| Native user | A single-user install without system-wide files | Python 3.12 or newer |
| Docker | Container-based deployments | Docker Engine and Docker Compose |
| Local development | Working from a source checkout | Python 3.12 or newer and Git; Node.js is needed to build frontend assets |

## Native installation

### System install

The installer defaults to the system scope. It needs permission to write under `/opt` and `/usr/local`.

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | sudo bash -s -- --native --system
```

The systemd service runs as the unprivileged `devlog` account. The installer does not create that account. Create it if it does not already exist:

```bash
sudo useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin devlog
```

Then create the configuration and administrator account:

```bash
sudo devlog onboard run --mode native --scope system --profile native-production
```

### User install

A user install does not need root. The launcher is placed in `${XDG_BIN_HOME:-~/.local}/bin`; add that directory to `PATH` if `devlog` is not found.

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native --user
devlog onboard run --mode native --scope user --profile native-production
```

Use an explicit `--scope` when running onboarding. If omitted, onboarding uses development paths in the current working directory. See [filesystem layout](filesystem-layout.md) for the paths used by each mode.

## Docker installation

Docker requires `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`. Copy the template, set strong secret values, and configure Redis for the Compose service. The template's `REDIS_URL` value points to localhost, so change it for Docker:

```bash
cp .env.example .env
```

Set these values in `.env`:

```dotenv
SECRET_KEY=<strong-random-secret>
ADMIN_PASSWORD=<strong-admin-password>
REDIS_URL=redis://redis:6379/0
BASE_URL=https://blog.example.com
```

`BASE_URL` should be the public URL when deploying behind a reverse proxy. Keep `.env` private.

### From a source checkout

```bash
git clone https://github.com/dbowm91/blog.git
cd blog
cp .env.example .env
```

After editing `.env`, build the images, run onboarding once to create the configuration and administrator, then start the services:

```bash
docker compose --profile production build
docker compose --profile production run --rm blog \
  devlog onboard run --mode docker --profile docker-production
docker compose --profile production up -d
```

Open <http://localhost:5000/admin/login>. The app listens on `127.0.0.1:5000`. Put a TLS-enabled reverse proxy in front of it before exposing it publicly.

### From the release installer

The installer places the Docker bundle in `/opt/devlog` and copies `.env.example` to `.env` if the file does not exist. Run it with elevated permissions, edit `.env` as above, then initialize and start DevLog:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | sudo bash -s -- --docker
cd /opt/devlog
docker compose --profile production build
docker compose --profile production run --rm blog \
  devlog onboard run --mode docker --profile docker-production
docker compose --profile production up -d
```

The Compose file has no default profile. The `production` profile starts the app, Redis, and the Celery worker. The optional `reverse-proxy` and `backup` profiles are documented in the [deployment guide](../DEPLOY.md).

Scheduled publishing, newsletters, and other scheduled jobs are disabled by default. To enable them, set `ENABLE_SCHEDULER=true` on exactly one app container.

## Local development

```bash
git clone https://github.com/dbowm91/blog.git
cd blog
./scripts/setup-dev.sh
FLASK_APP=run:app venv/bin/python -m flask create-admin
venv/bin/python run.py
```

The setup script creates a virtual environment, generates local credentials, installs dependencies, and applies database migrations. `create-admin` prompts for the first administrator account. Open <http://localhost:5000/admin/login> after the server starts.

For plain HTTP testing, set both `DEBUG=true` and `SESSION_COOKIE_SECURE=false` in `.env`. Debug mode enables the Werkzeug debugger. Use it only on a local machine and do not expose the server publicly. For production, keep secure cookies enabled and use HTTPS.

## Onboarding

Onboarding creates or updates configuration, runtime directories, database schema, and the initial administrator. Always provide the correct install mode and scope:

```bash
devlog onboard run --mode native --scope system --profile native-production
devlog onboard run --mode native --scope user --profile native-production
devlog onboard run --mode docker --profile docker-production
```

Docker mode ignores `--scope`. Do not omit `--scope` for native installs, because omission selects the development layout rather than detecting the installation.

For unattended native setup, provide the administrator password through a protected file instead of a command-line argument:

```bash
devlog onboard run \
  --non-interactive \
  --mode native \
  --scope system \
  --profile native-production \
  --admin-password-file /path/to/password.txt \
  --admin-username admin \
  --site-url https://blog.example.com
```

### Previewing onboarding

`--dry-run` skips configuration and environment-file writes, but path resolution still creates the configuration and data directories. It is not a no-change filesystem operation.

```bash
devlog onboard run --mode native --scope system --profile native-production --dry-run
```

Re-running onboarding rewrites `.env` from a fixed set of supported keys. Keep custom environment settings in `config.toml` or re-add them after onboarding. Progress metadata is stored separately as `onboarding-metadata.json` in the data directory.

## Configuration

DevLog reads non-secret settings from `config.toml`. Environment variables take precedence, then `config.toml`, then built-in defaults. Keep secrets such as `SECRET_KEY`, `ADMIN_PASSWORD`, and SMTP credentials in the environment or `.env`, not in `config.toml`.

Useful commands:

```bash
devlog config check
devlog config show --effective
devlog config explain email.smtp_host
devlog config paths
```

See [`config.toml.example`](../config.toml.example) for the available settings.

## Database and backups

SQLite is the default and recommended production database for a single server. PostgreSQL and other non-SQLite databases are experimental; SQLite-specific search and integrity checks are unavailable for them.

```bash
devlog db status
devlog db check
devlog db migrate
devlog db rebuild-search
```

Create and inspect backups with:

```bash
devlog backup create
devlog backup verify /path/to/backup
devlog backup inspect /path/to/backup
```

Encrypted backups require `BACKUP_ENCRYPTION_KEY`. See the [backup guide](../architecture/services/backup.md) for details.

## Themes

Use **Settings > Theme** in the admin dashboard to choose dark and light themes, preview changes, and set the default color scheme. For custom themes, see the [theme operator guide](themes/operator-guide.md).

## Troubleshooting

### Admin login does not keep the session

For local HTTP testing only, set `DEBUG=true` and `SESSION_COOKIE_SECURE=false`. Do not use this setting in production. Use HTTPS for a public site.

### Search is unavailable or stale

Rebuild the SQLite full-text search index:

```bash
devlog db rebuild-search
```

### Scheduled jobs do not run

Set `ENABLE_SCHEDULER=true` on exactly one app container. Enabling it on multiple containers can run jobs more than once.

### Port 5000 is already in use

Set `SERVER_PORT` in the environment or change `port` under `[server]` in `config.toml`.

## Further reading

- [Filesystem layout](filesystem-layout.md)
- [Migration planning from a checkout](migration-from-checkout.md)
- [Operator CLI reference](../architecture/deployment/cli.md)
- [Deployment guide](../DEPLOY.md)
