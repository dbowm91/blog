# DevLog

A self-hosted Flask blog CMS for technical writing, newsletters, feeds, analytics, and admin-managed content.

[![CI](https://github.com/dbowm91/blog/actions/workflows/ci.yml/badge.svg)](https://github.com/dbowm91/blog/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## What is DevLog?

**DevLog** is a self-hosted blog platform designed for developers and technical writers who want full control over their content, subscribers, and data.

### Who is it for?

- Developers who want a simple, fast blog they can deploy on their own server
- Technical writers who need Markdown editing, code highlighting, and newsletter support
- Anyone who prefers owning their data over using a hosted platform

### What it is not

- Not a full CMS like WordPress — it focuses on blog posts, pages, and newsletters
- Not a SaaS — you run it on your own infrastructure
- Not a static site generator — it runs as a dynamic Flask application

### Core Features

- **Markdown Posts** — Write with a live preview editor, auto-save drafts, schedule publishing
- **Admin Dashboard** — Manage posts, pages, tags, subscribers, media, and analytics
- **Newsletter** — Send newsletters to confirmed subscribers with retry logic
- **Feeds** — RSS 2.0, Atom 1.0, and JSON Feed 1.1 endpoints
- **Tags & Series** — Organize posts with tags and multi-part series
- **Full-Text Search** — SQLite FTS5-powered search with snippets
- **REST API** — Manage posts, pages, tags, subscribers, and series via API
- **2FA** — TOTP-based two-factor authentication for admin accounts
- **Backups** — Encrypted (AES-256-GCM) and compressed backups with restore
- **Theming** — Halloy-compatible TOML theme system with 50 bundled themes, admin selector with live preview, dark/light scheme support, and custom CSS
- **Analytics** — Page views, referrers, and share tracking
- **Media Library** — Upload and manage images with local storage (S3 support is experimental)
- **Static Pages** — Create standalone pages at custom slugs
- **Comments** — Moderated comments with spam filtering
- **Security** — CSRF protection, rate limiting, security headers, session IP binding

---

## Quick Start

### Docker Production (Recommended)

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
cp .env.example .env
# Edit .env: set SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

Docker builds frontend assets (Vite) automatically inside the container. No local Node.js installation required.

The app binds to `127.0.0.1:5000` (localhost only). For public access, terminate TLS with a host-level reverse proxy (Caddy, nginx, Traefik) and proxy to `http://127.0.0.1:5000`. See [DEPLOY.md § Reverse Proxy Setup](DEPLOY.md#9-reverse-proxy-setup) for examples.

> **Local HTTP testing:** Set `SESSION_COOKIE_SECURE=false` in your `.env` when testing at `http://localhost:5000`, otherwise admin login cookies will not persist. Never use `SESSION_COOKIE_SECURE=false` in production behind HTTPS.

### Local Development

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
./setup.sh
venv/bin/python run.py
```

This creates a virtual environment, generates secure credentials, and loads the `.env` file.

### CLI Installation

DevLog provides a standalone `devlog` CLI for operator tasks:

```bash
pip install .
devlog --help
devlog --version
```

For development (editable install with dev dependencies):

```bash
pip install -e '.[dev]'
```

The CLI does not require Flask app context for `--help` and `--version`. Global options:

```bash
devlog --json version       # JSON output
devlog --verbose config     # Verbose help
devlog --quiet db           # Minimal output
```

Command groups: `config`, `admin`, `db`, `data`, `themes`, `backup`. The `config` group provides typed configuration management commands.

### Access Your Blog

Visit `http://localhost:5000`. Admin panel at `http://localhost:5000/admin/login`.

### Write Your First Post

1. Log in at `/admin/login`
2. Click **New Post** in the dashboard
3. Enter a title, write in Markdown
4. Add tags (comma-separated)
5. Click **Publish**

### Set Up Newsletter (Optional)

1. Configure SMTP in `config.toml` under `[email]`
2. Set `SMTP_USER` and `SMTP_PASSWORD` environment variables
3. Add subscribers via `/subscribe` or the API
4. Send newsletters from `/admin/subscribers`

For production deployment, see [DEPLOY.md](DEPLOY.md).

### Configuration Management

DevLog includes a typed configuration system at `app/config/` with 20 frozen dataclasses, multi-layer validation, and deployment profiles. Use the `devlog` CLI for configuration management:

```bash
devlog config check              # Validate configuration
devlog config show --effective   # Show resolved values with sources
devlog config explain email.smtp_host  # Explain a specific field
devlog config init --profile development  # Generate config from profile
```

---

## Building Frontend Assets

Docker builds frontend assets automatically via a multi-stage build. For non-Docker deployments:

```bash
npm ci
npm run build
```

This generates content-hashed assets in `app/static/dist/` with a `manifest.json`. The app's `vite_asset()` helper resolves hashed filenames. Without this build, templates fall back to the unbundled source paths, so production JavaScript code-splitting will not work correctly.

---

## How-To: Common Tasks

### Writing Posts

**Markdown Tips:**
- Add `---` as a divider to set summary/excerpt
- Use `## Heading` (h2) and `### Heading` (h3) for automatic table of contents
- Drag images into the editor to upload
- Drafts auto-save to localStorage

**Previewing:**
Click **Preview** to see how your post will look with theme styling.

### Sending Newsletters

1. Write and publish your post
2. Go to **Subscribers** in the admin sidebar
3. Click **Send Newsletter**
4. Newsletter sends to all confirmed subscribers at `config.toml` `[newsletter] send_time`

**Troubleshooting:**
- No subscribers? Visit `/subscribe` on your blog
- Confirmation emails not arriving? Check SMTP settings and `SMTP_USER`/`SMTP_PASSWORD` env vars
- Newsletter not sending? Check `logs/blog.log`

### Managing Subscribers

- **Add via API:** `POST /api/subscribers` with `{"email": "user@example.com"}` using `X-API-Key`
- **Bulk resend confirmation:** Select subscribers → "Resend Confirmation" bulk action
- **Export:** Click **Export CSV** in `/admin/subscribers`
- **Unsubscribe:** Each email includes `/unsubscribe/<token>` link

### Scheduling Posts

1. Set **Publish At** to a future datetime when editing a post
2. Scheduler runs every 5 minutes and publishes automatically (requires `ENABLE_SCHEDULER=true`)
3. Scheduled posts show a clock icon in the dashboard

### Customizing Appearance

1. Go to `/admin/settings`
2. Choose a **Dark Theme** and **Light Theme** from 50+ bundled Halloy themes
3. Set **Default Color Scheme** (`system` respects OS preference, `dark`, or `light`)
4. Optionally enable **Custom CSS**
5. Set **Logo Text** or leave blank to use site title

**Custom Themes:** Place Halloy-compatible `.toml` files in the external themes directory (configured via `THEME_EXTERNAL_DIR` or `config.toml` `[themes]` section). External themes override bundled themes with the same name.

**Accessibility:** Themes are classified into three tiers — **recommended** (zero failures), **compatible-with-exceptions** (documented deviations), and **experimental** (unexpected failures). All bundled themes satisfy mandatory accessibility thresholds. Run `flask themes accessibility --strict` to verify. See [docs/themes/operator-guide.md § Accessibility Policy](docs/themes/operator-guide.md#accessibility-policy) for details.

**CLI Management:**
```bash
devlog themes list                    # List all available themes
devlog themes validate ./my-theme.toml  # Validate a theme file
devlog themes inspect "Catppuccin Mocha"  # Inspect theme details
devlog themes refresh                 # Refresh theme registry
devlog themes accessibility           # Run WCAG contrast checks (--strict for mandatory-only)
# Flask commands remain as compatibility wrappers:
# flask themes list, flask themes validate, etc.
```

See [docs/themes/operator-guide.md](docs/themes/operator-guide.md) for the full operator guide and [docs/themes/supported-schema.md](docs/themes/supported-schema.md) for the Halloy TOML schema reference.

### Managing Tags

1. Go to `/admin/tags`
2. Click **New Tag** to create
3. Edit or delete existing tags
4. Tags appear in the sidebar and can be filtered

### Adding Static Pages

1. Go to `/admin/pages`
2. Click **New Page**
3. Write content in Markdown
4. Pages appear at `/page/<slug>`

### User Management

- **Create admin:** `devlog admin create <username>` (or `flask create-admin <username>`)
- **Promote user:** `devlog admin promote <username>` (or `POST /admin/users/<id>/promote`)
- **Demote admin:** `POST /admin/users/<id>/demote`
- **Transfer ownership:** `POST /admin/users/<id>/make-owner`
- **Password reset:** `devlog admin reset-password <username>` or visit `/admin/forgot-password`

### Media Library

1. Go to `/admin/media`
2. Upload images (JPEG, PNG, GIF, WebP)
3. Click an image to copy its URL or delete it

### Accessing Feeds

- **RSS Feed:** `/rss`
- **JSON Feed:** `/json`
- Add `?limit=N` to limit number of items

---

## Support Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| SQLite with WAL | Supported | Default single-server database for v1 |
| PostgreSQL | Experimental | Not recommended for v1 production; health checks report unsupported for SQLite-specific features |
| Local filesystem media | Supported | Default media backend |
| S3-compatible media | Experimental | Requires boto3; not CI-tested |
| Redis (cache/rate limiting) | Supported | Used in Docker production profile |
| Celery + Redis (async tasks) | Supported | Newsletter, webhooks, image variants; included in production compose profile |
| External TLS reverse proxy | Supported/recommended | Caddy/nginx/Traefik/cloud proxy to localhost app |
| Included nginx profile | Optional/advanced | Requires `--profile reverse-proxy` and certificate configuration |
| Metrics endpoint | Supported when enabled | Disabled by default; secret required in production |
| Detailed health | Supported when protected | Basic health remains public; detailed health requires secret in production |
| Typed configuration | Supported | 20 frozen dataclasses, multi-layer validation, deployment profiles, CLI management |

See [DEPLOY.md § Support Matrix](DEPLOY.md#support-matrix) for details.

---

## Reference

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key (32+ chars) |
| `ADMIN_PASSWORD` | Yes | Admin login password |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASSWORD` | No | SMTP password |
| `SESSION_COOKIE_SECURE` | No | Require HTTPS for cookies. Set `false` for local HTTP (default: `true`) |
| `API_KEY` | No | REST API authentication |
| `DATABASE_URL` | No | Non-SQLite database URL (experimental — falls back to SQLite if unset) |
| `REDIS_URL` | No | Redis connection URL for cache/Celery (default: `redis://localhost:6379/0`) |
| `ENABLE_SCHEDULER` | No | Enable APScheduler for newsletters and backups (default: `false`, set `true` on exactly ONE container) |
| `HEALTH_CHECK_SECRET` | No | Secret for detailed `/health?detailed=true` endpoint |
| `METRICS_SECRET` | No | Secret for `/metrics` endpoint (no fallback; must be set with `ENABLE_METRICS`) |
| `ENABLE_METRICS` | No | Enable `/metrics` endpoint (default: `false`; set `true` with `METRICS_SECRET` in production) |

**Note:** The typed configuration system (`app/config/`) supports all these environment variables with precedence: env vars > config.toml > defaults. Use `devlog config explain <field>` to see the full mapping for any config field.

### CLI Commands

```bash
flask create-admin <username>     # Create admin user
flask promote-admin <username>    # Promote to admin
flask rebuild-search              # Rebuild FTS5 index
flask cleanup-orphaned-images     # Remove unused images (equivalent to devlog media cleanup)
flask check-integrity            # Verify database integrity
flask export-data <file>         # Export data to JSON
flask import-data <file>        # Import data from JSON
flask seed                       # Generate sample data
flask shell                      # Interactive shell
flask themes list                # List available themes
flask themes validate <path>     # Validate a theme file or name
flask themes inspect <name>      # Inspect theme details
flask themes refresh             # Refresh theme registry
flask themes paths               # Show theme resource paths
flask themes accessibility       # Run WCAG contrast checks (--strict for mandatory-only, --json for structured output)

# Typed configuration management (via devlog CLI)
devlog config check              # Validate configuration with multi-layer checks
devlog config show               # Display current config (secrets redacted)
devlog config explain <field>    # Explain a specific config field
devlog config paths              # Show config file resolution paths
devlog config init --profile <name>  # Generate config from deployment profile
devlog config migrate            # Migrate config to current version

# Operations (via devlog CLI)
devlog admin create <username>   # Create admin user
devlog admin promote <username>  # Promote to admin
devlog admin reset-password <username>  # Reset admin password
devlog admin list                # List admin users
devlog db check                  # Check SQLite integrity
devlog db rebuild-search         # Rebuild FTS5 index
devlog db status                 # Show Alembic migration status
devlog db migrate                # Apply pending database migrations
devlog data export <file>        # Export data to JSON
devlog data import <file>        # Import data from JSON
devlog media scan                # Scan for orphaned media files (dry run)
devlog media cleanup             # Clean up orphaned media files (--apply to delete)
devlog themes list               # List available themes
devlog themes validate <path>    # Validate a theme file or name
devlog themes inspect <name>     # Inspect theme details
devlog themes refresh            # Refresh theme registry
devlog themes paths              # Show theme resource paths
devlog themes accessibility      # Run WCAG contrast checks (--strict for mandatory-only)
devlog backup create             # Create a backup
devlog backup verify <filename>  # Verify backup integrity
```

> **Note:** Flask commands (`flask ...`) delegate to the same service layer as the standalone `devlog` CLI. The `devlog` CLI is the recommended interface for scripting and automation.

### API Endpoints

See `docs/openapi.yaml` for full API documentation.

Authentication uses either the legacy `API_KEY` environment variable (grants all scopes) or scoped `ApiToken` objects. Scoped tokens support exact matches, `admin:*` for full access, and category wildcards (e.g. `posts:*` grants `posts:read` and `posts:write`).

| Endpoint | Method | Description |
|---|---|---|
| `/api/posts` | GET | List posts (supports `?page=`, `?per_page=`, `?published=`) |
| `/api/posts/<id>` | GET | Get single post by ID |
| `/api/posts` | POST | Create post (requires API key) |
| `/api/posts/<id>` | PUT | Update post |
| `/api/posts/<id>` | DELETE | Delete post |
| `/api/subscribers` | GET | List subscribers |
| `/api/subscribers` | POST | Add subscriber |
| `/api/tags` | GET | List tags |
| `/api/pages` | GET | List pages |
| `/api/series` | GET | List series |
| `/api/stats` | GET | Get site statistics |

### Database Models

Key tables: `users`, `posts`, `tags`, `subscribers`, `pages`, `page_views`, `share_events`, `admin_sessions`, `site_settings`, `post_revisions`, `webhooks`, `webhook_events`, `series`, `post_series`, `comments`, `admin_audit_logs`, `api_tokens`

### Ports

- Development server: `0.0.0.0:5000`
- Docker production: `127.0.0.1:5000` (localhost only — use a reverse proxy for public access)

---

## Project Status

DevLog is actively maintained. The core feature set is stable and well-tested.

## Non-Goals

- Multi-tenant SaaS hosting
- Plugin/extension system
- Built-in WYSIWYG editor (Markdown-only)
- Real-time collaboration
- Native mobile apps

---

## Troubleshooting

### "RuntimeError: ADMIN_PASSWORD is required"

```bash
export ADMIN_PASSWORD="your-password"
python run.py
```

### "RuntimeError: SECRET_KEY is required"

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
python run.py
```

### Posts not appearing on homepage

- Check post is **Published** (not draft)
- Verify `base_url` in `config.toml` is correct
- Check post's **Created At** date is not in the future

### Search returns no results

1. Rebuild: `flask rebuild-search`
2. Check FTS5: look for `posts_fts` table in database
3. Try simpler terms (FTS5 prefix mode)

### Newsletter not sending

1. Verify SMTP credentials
2. Check `config.toml` `[email]` section
3. Look in `logs/blog.log`
4. Ensure subscribers are **Confirmed**

### Images not uploading

- Check `app/static/uploads/` exists and is writable
- Verify file size under 16 MB
- Allowed types: JPEG, PNG, GIF, WebP, SVG

### Database locked errors

- Another process is writing
- Use `--workers 1` with multiple workers for newsletter
- Restart to clear stale connections

### High memory usage

- Reduce workers in Granian/Gunicorn
- Check `logs/blog.log` for leaks
- Run `flask cleanup-orphaned-images`

### CSS changes not applying

- Hard refresh: `Ctrl+Shift+R` / `Cmd+Shift+R`
- Verify Custom CSS is enabled in `/admin/settings`
- Check CSS syntax in Custom CSS editor

---

## Full Documentation

- [DEPLOY.md](DEPLOY.md) — Production deployment, Docker, PostgreSQL migration, systemd, monitoring
- [USAGE.md](USAGE.md) — Detailed user guide for all admin features
- [ARCHITECTURE.md](architecture/overview.md) — System design, data flow, and component relationships
- [CONTRIBUTING.md](CONTRIBUTING.md) — Developer setup and contribution guidelines
- [SECURITY.md](SECURITY.md) — Security features and vulnerability reporting
- [AGENTS.md](AGENTS.md) — Developer/contributor guidelines
- [Theme Operator Guide](docs/themes/operator-guide.md) — Theme selection, external themes, CLI commands
- [Theme Schema Reference](docs/themes/supported-schema.md) — Halloy TOML schema for theme authors
- [Theme Token Contract](docs/themes/blog-theme-contract.md) — BlogTheme semantic token matrix
- [Legacy Compatibility](docs/themes/legacy-compatibility.md) — Migration from legacy presets
