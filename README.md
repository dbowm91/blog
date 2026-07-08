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
- **Theming** — CSS custom properties with theme presets (GitHub Dark/Light, Solarized, Monokai)
- **Analytics** — Page views, referrers, and share tracking
- **Media Library** — Upload and manage images with local storage (S3 support is experimental)
- **Static Pages** — Create standalone pages at custom slugs
- **Comments** — Moderated comments with spam filtering
- **Security** — CSRF protection, rate limiting, security headers, session IP binding

---

## Quick Start

Get from zero to a running blog in 5 minutes.

### Option A: Docker (Recommended for Production)

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
cp .env.example .env
# Edit .env with your SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

Docker builds frontend assets (Vite) automatically inside the container. No local Node.js installation required.

### Option B: Local Development

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
./setup.sh
python run.py
```

This creates a virtual environment, generates secure credentials, and loads the `.env` file. Then starts the dev server.

### 2. Access Your Blog

Visit `http://localhost:5000`. Admin panel at `http://localhost:5000/admin/login`.

### 3. Write Your First Post

1. Log in at `/admin/login`
2. Click **New Post** in the dashboard
3. Enter a title, write in Markdown
4. Add tags (comma-separated)
5. Click **Publish**

### 4. Set Up Newsletter (Optional)

1. Configure SMTP in `config.toml` under `[email]`
2. Set `SMTP_USER` and `SMTP_PASSWORD` environment variables
3. Add subscribers via `/subscribe` or the API
4. Send newsletters from `/admin/subscribers`

For production deployment, see [DEPLOY.md](DEPLOY.md).

---

## Building Frontend Assets

Docker builds frontend assets automatically via a multi-stage build. For non-Docker deployments:

```bash
npm ci
npm run build
```

This generates content-hashed assets in `app/static/dist/` with a `manifest.json`. The app's `vite_asset()` helper resolves hashed filenames. Without this build, JavaScript assets will return 404 in production.

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
2. Choose a **Theme Preset** (GitHub Dark, GitHub Light, Solarized Dark, Monokai)
3. Optionally enable **Custom CSS**
4. Set **Logo Text** or leave blank to use site title

**CSS Custom Properties:**
```css
:root {
    --accent: #ff6600;
    --bg: #1a1a2e;
    --bg-surface: #252542;
    --text: #e0e0e0;
    --text-muted: #888;
    --border: #3a3a5c;
}
```

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

- **Create admin:** `flask create-admin <username>`
- **Promote user:** `POST /admin/users/<id>/promote`
- **Demote admin:** `POST /admin/users/<id>/demote`
- **Transfer ownership:** `POST /admin/users/<id>/make-owner`
- **Password reset:** Visit `/admin/forgot-password`

### Media Library

1. Go to `/admin/media`
2. Upload images (JPEG, PNG, GIF, WebP, SVG)
3. Click an image to copy its URL or delete it

### Accessing Feeds

- **RSS Feed:** `/rss`
- **JSON Feed:** `/json`
- Add `?limit=N` to limit number of items

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
| `DATABASE_URL` | No | PostgreSQL connection string (experimental, overrides SQLite) |

### CLI Commands

```bash
flask create-admin <username>     # Create admin user
flask promote-admin <username>    # Promote to admin
flask rebuild-search              # Rebuild FTS5 index
flask cleanup-orphaned-images     # Remove unused images
flask check-integrity            # Verify database integrity
flask export-data <file>         # Export data to JSON
flask import-data <file>        # Import data from JSON
flask seed                       # Generate sample data
flask shell                      # Interactive shell
```

### API Endpoints

See `docs/openapi.yaml` for full API documentation.

| Endpoint | Method | Description |
|---|---|---|
| `/api/posts` | GET | List posts (supports `?q=`, `?page=`, `?per_page=`, `?published=`) |
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

Key tables: `posts`, `users`, `tags`, `subscribers`, `page_views`, `share_events`, `admin_sessions`, `site_settings`, `pages`, `post_revisions`

### Ports

- Development server: `0.0.0.0:5000`
- Granian (production): `127.0.0.1:5000`

---

## Project Status

DevLog is production-ready and actively maintained. The core feature set is stable and well-tested.

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
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, data flow, and component relationships
- [CONTRIBUTING.md](CONTRIBUTING.md) — Developer setup and contribution guidelines
- [SECURITY.md](SECURITY.md) — Security features and vulnerability reporting
- [AGENTS.md](AGENTS.md) — Developer/contributor guidelines
