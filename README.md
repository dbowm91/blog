# DevLog

A personal blog platform built with Flask, featuring an admin dashboard, newsletter, RSS/JSON feeds, and analytics.

---

## Tutorial: Getting Started

Get from zero to a running blog in 5 minutes.

### 1. Clone and Install

```bash
git clone <repo-url> /opt/blog
cd /opt/blog
./setup.sh
```

This creates a virtual environment, generates secure credentials, and starts the dev server.

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
2. Scheduler runs every 5 minutes and publishes automatically
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

- **RSS Feed:** `/rss.xml`
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
| `SESSION_COOKIE_SECURE` | No | Require HTTPS (default: `true`) |
| `API_KEY` | No | REST API authentication |

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
| `/api/posts` | GET | List posts (supports `?q=`, `?page=`, `?per_page=`) |
| `/api/posts/<slug>` | GET | Get single post |
| `/api/posts` | POST | Create post (requires API key) |
| `/api/posts/<slug>` | PUT | Update post |
| `/api/posts/<slug>` | DELETE | Delete post |
| `/api/subscribers` | GET | List subscribers |
| `/api/subscribers` | POST | Add subscriber |

### Database Models

Key tables: `posts`, `users`, `tags`, `subscribers`, `page_views`, `share_events`, `admin_sessions`, `site_settings`, `pages`, `post_revisions`

### Ports

- Development server: `0.0.0.0:5000`
- Granian (production): `127.0.0.1:5000`

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

## Explanation: Architecture

### Why SQLite by Default?

SQLite with WAL mode provides:
- Single-file backup (simple `cp` or `.backup`)
- No separate server process
- Excellent read performance for <10,000 posts
- Concurrent reads while writing

For higher traffic or multi-server deployments, migrate to PostgreSQL. See [DEPLOY.md](DEPLOY.md#postgresql-migration-guide).

### Why Granian?

Granian is a Rust-based ASGI server that outperforms Python alternatives (Uvicorn, Gunicorn) in benchmarks. Use:

```bash
granian --interface asgi --workers 4 --timeout 60 run:asgi_app
```

### Why APScheduler for Newsletter?

The newsletter uses in-process APScheduler with file locking (`fcntl`) for single-machine deployments. For multi-machine setups, use an external scheduler (Celery, cron) or distributed lock (Redis).

### Storage Abstraction

The `app/storage.py` module abstracts file storage between local filesystem and S3-compatible backends. Configure via `STORAGE_BACKEND` environment variable.

### Session Security

- Sessions expire after 24 hours of inactivity
- IP binding warns on address change (doesn't invalidate)
- CSRF tokens use sliding window (5 tokens)

### Security Headers

The app sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (when HTTPS)
- `Content-Security-Policy` (self-only, nonces for scripts)

---

## Full Documentation

- [DEPLOY.md](DEPLOY.md) — Production deployment, Docker, PostgreSQL migration, systemd, monitoring
- [USAGE.md](USAGE.md) — Detailed user guide for all admin features
- [AGENTS.md](AGENTS.md) — Developer/contributor guidelines
