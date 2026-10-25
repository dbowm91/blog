# DevLog

Self-hosted blog CMS for technical writers — Markdown posts, pages, a newsletter,
feeds, full-text search, comments, and a themed admin dashboard. Flask, SQLite
or PostgreSQL, no external services required.

[![CI](https://github.com/dbowm91/blog/actions/workflows/ci.yml/badge.svg)](https://github.com/dbowm91/blog/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/dbowm91/blog.git && cd blog
cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

Open <http://localhost:5000>, then log in at `/admin/login`.

The build compiles the frontend in a container, so Node.js is not needed. The app
binds `127.0.0.1:5000` — put a TLS-terminating reverse proxy (Caddy, nginx,
Traefik) in front of it for public access.

### Native install

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
devlog onboard run --mode native
```

The installer fetches a verified release artifact and creates a `devlog`
launcher; onboarding then generates the config, secrets and admin account. Add
`--system` for `/opt/devlog` (needs root) or `--user` for `~/.local`.

### Local development

```bash
git clone https://github.com/dbowm91/blog.git && cd blog
./scripts/setup-dev.sh
venv/bin/python run.py
```

`setup-dev.sh` creates a virtualenv, installs dependencies, and writes `.env`
with generated credentials.

> Testing over plain HTTP? Set `SESSION_COOKIE_SECURE=false` in `.env`, or the
> admin login cookie will not persist. Never do this in production behind HTTPS.

---

## Example usage

**Write a post.** Log in at `/admin/login` → **New Post** → write Markdown →
add tags → **Publish**. Use `---` on its own line to set the excerpt, `##` and
`###` headings to build the table of contents, and drag images into the editor
to upload them. Drafts auto-save.

**Publish on a schedule.** Set **Publish At** to a future date. The scheduler
publishes it automatically every 5 minutes (`ENABLE_SCHEDULER=true` on exactly
one container).

**Subscribe a reader.** Point them at `/subscribe`. They confirm by email, then
appear under **Subscribers**. Send the newsletter from `/admin/subscribers`, or
let the scheduled job send it at the `[newsletter] send_time` in `config.toml`.

**Drive it from the shell.**

```bash
devlog doctor                      # diagnose the installation
devlog config check                # validate configuration
devlog admin create alice          # create an admin account
devlog db rebuild-search           # rebuild the FTS5 index
devlog backup create               # take a backup
devlog paths status                # show where everything lives
```

**Use the REST API.** Authenticate with the `X-API-Key` header — either the
legacy `API_KEY` environment variable or a scoped `ApiToken` (exact scopes,
`admin:*`, or category wildcards like `posts:*`).

```bash
# List published posts
curl -s http://localhost:5000/api/posts?published=true \
  -H "X-API-Key: $API_KEY"

# Create a post
curl -s -X POST http://localhost:5000/api/posts \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"title":"Hello","content":"# Hi\n\nFirst post.","published":false}'

# Add a subscriber
curl -s -X POST http://localhost:5000/api/subscribers \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"email":"reader@example.com"}'
```

**Pick a theme.** `/admin/settings` offers 50 bundled Halloy themes with a live
preview, plus dark/light/system colour-scheme control, typeface selection (10
self-hosted families) and page backdrops. Drop your own `.toml` into the
external themes directory to override a bundled theme.

**Consume the feeds.** `/rss` (RSS 2.0), `/atom` (Atom 1.0), `/json` (JSON Feed
1.1). Add `?limit=N` to cap the item count.

---

## Features

| | |
|---|---|
| **Writing** | Markdown editor with live preview, autosave drafts, scheduled publishing, revisions with diff |
| **Content** | Posts, pages, tags, series, threaded comments, custom slugs, page menu |
| **Distribution** | RSS/Atom/JSON feeds, newsletter with retry logic, webhooks with HMAC signing |
| **Discovery** | SQLite FTS5 full-text search with snippets and BM25 ranking |
| **Admin** | Dashboard analytics, media library, subscriber management, audit log, multi-admin sessions |
| **Theming** | 50 Halloy themes, 10 self-hosted font families, backdrops, custom CSS, dark/light/system scheme |
| **Security** | TOTP 2FA with backup codes, CSRF protection, rate limiting, session IP binding, SSRF-safe webhooks |
| **Operations** | `devlog` CLI, typed configuration, health and metrics endpoints, encrypted backups |

---

## Configuration

Configuration lives in `config.toml`; environment variables override it, and
defaults apply when neither is set. `devlog config explain <field>` documents
any field.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Session signing key (32+ chars) |
| `ADMIN_PASSWORD` | Yes | Initial admin password |
| `ADMIN_USERNAME` | No | Admin username (default `admin`) |
| `API_KEY` | No | REST API key — grants all scopes |
| `SMTP_USER` / `SMTP_PASSWORD` | No | SMTP credentials for the newsletter |
| `REDIS_URL` | No | Cache, rate limits and Celery broker |
| `DATABASE_URL` | No | PostgreSQL instead of SQLite (experimental) |
| `ENABLE_SCHEDULER` | No | Run APScheduler — set `true` on exactly **one** container |
| `HEALTH_CHECK_SECRET` | No | Protects `/health?detailed=true` |
| `ENABLE_METRICS` / `METRICS_SECRET` | No | Enables `/metrics` (off by default) |
| `SESSION_COOKIE_SECURE` | No | Defaults `true`; set `false` only for local HTTP |

`config.toml.example` lists every option. Only the example is committed —
`config.toml` is gitignored.

---

## Documentation

| Document | Covers |
|---|---|
| [DEPLOY.md](DEPLOY.md) | Production deployment, Docker, systemd, PostgreSQL, monitoring |
| [USAGE.md](USAGE.md) | Every admin feature, end to end |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design — starts at the [module map](architecture/overview.md) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and commit conventions |
| [SECURITY.md](SECURITY.md) | Security model and vulnerability reporting |
| [docs/](docs/) | Operator guides, the API reference, and theme authoring |
| [docs/themes/](docs/themes/) | The Halloy theme schema, token contract and operator guide |
| [docs/openapi.yaml](docs/openapi.yaml) | OpenAPI spec (also served at `/api/docs`) |
| [AGENTS.md](AGENTS.md) | Conventions for coding agents |
| [.skills/](.skills/) | Agent-facing skills: codebase map, architecture review, release validation |

---

## Development

```bash
./scripts/setup-dev.sh          # venv, dependencies, .env
npm ci && npm run build          # build the frontend bundle
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 \
  python3 -m pytest tests/       # run the tests
```

Run `npm run build` before serving in production — the app reads the Vite
manifest to resolve content-hashed asset filenames.

---

## License

MIT — see [LICENSE](LICENSE).
