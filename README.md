# DevLog

A personal blog platform built with Flask, featuring an admin dashboard, newsletter, RSS feed, and analytics.

## Quick Start

Get from zero to running in 5 minutes:

```bash
git clone <repo-url> /opt/blog
cd /opt/blog
./setup.sh
```

This creates a virtual environment, generates secure credentials, and starts the dev server. Visit `http://localhost:5000`. Admin at `http://localhost:5000/admin/login`.

For production, see [DEPLOY.md](DEPLOY.md).

---

## Common Tasks

### Writing a Post

1. Log in at `/admin/login`
2. Click **New Post** in the dashboard
3. Enter title, write in Markdown, add tags
4. Click **Publish** (or schedule via **Publish At**)
5. Use the **Preview** button to see how it looks

**Tips:**
- Add a `---` divider in Markdown to set a summary/excerpt
- Use `## Heading` (h2) and `### Heading` (h3) for automatic table of contents
- Drag images into the editor to upload
- Your draft saves to localStorage automatically

### Sending a Newsletter

1. Write and publish your post
2. Go to **Subscribers** in the admin sidebar
3. Click **Send Newsletter** button
4. The newsletter sends to all confirmed subscribers at the scheduled time (`config.toml` `[newsletter] send_time`)

**Troubleshooting:**
- No subscribers? Visit `/subscribe` on your blog to let people sign up
- Confirmation emails not arriving? Check SMTP settings in `config.toml` and `SMTP_USER`/`SMTP_PASSWORD` env vars
- Newsletter not sending? Check `logs/blog.log` for scheduler errors

### Managing Subscribers

- **Add manually:** POST to `/api/subscribers` with `{"email": "user@example.com"}` using the API key
- **Bulk resend confirmation:** Select subscribers in `/admin/subscribers`, choose "Resend Confirmation" from bulk actions
- **Export:** Click **Export CSV** in `/admin/subscribers`
- **Unsubscribe:** Each email includes an unsubscribe link (`/unsubscribe/<token>`)

### Scheduling Posts

1. When editing a post, set **Publish At** to a future datetime
2. The scheduler runs every 5 minutes and publishes automatically
3. Scheduled posts appear in the dashboard with a clock icon

### Customizing Appearance

1. Go to `/admin/settings`
2. Choose a **Theme Preset** (GitHub Dark, GitHub Light, Solarized Dark, Monokai)
3. Optionally enable **Custom CSS** for additional styling
4. Set a **Logo Text** or leave blank to use site title

CSS custom properties available:
```css
:root {
    --accent: #ff6600;      /* links, buttons */
    --bg: #1a1a2e;           /* page background */
    --bg-surface: #252542;  /* cards, surfaces */
    --text: #e0e0e0;         /* primary text */
    --text-muted: #888;     /* secondary text */
    --border: #3a3a5c;      /* borders */
}
```

### Adding Static Pages

1. Go to `/admin/pages`
2. Click **New Page**
3. Write content in Markdown
4. Pages appear at `/page/<slug>`

### User Management

- **Create admin:** `flask create-admin <username>`
- **Promote user:** `POST /admin/users/<id>/promote` (makes admin)
- **Demote admin:** `POST /admin/users/<id>/demote` (removes admin)
- **Transfer ownership:** `POST /admin/users/<id>/make-owner`
- **Password reset:** Visit `/admin/forgot-password`

### Media Library

1. Go to `/admin/media`
2. Upload images (JPEG, PNG, GIF, WebP, SVG)
3. Click an image to copy its URL or delete it

Images are stored in `app/static/uploads/`. Include in backups.

---

## Troubleshooting

### "RuntimeError: ADMIN_PASSWORD is required"

Set the environment variable before running:
```bash
export ADMIN_PASSWORD="your-password"
python run.py
```

### "RuntimeError: SECRET_KEY is required"

Generate and set a secret key:
```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
python run.py
```

### Login页面不加载 / Login page shows error

1. Check `logs/blog.log` for errors
2. Verify `SECRET_KEY` and `ADMIN_PASSWORD` are set
3. Try clearing browser cookies

### Posts not appearing on homepage

- Check post is **Published** (not draft)
- Verify `base_url` in `config.toml` is correct
- Check post's **Created At** date is not in the future

### Search returns no results

1. Rebuild the search index: `flask rebuild-search`
2. Check FTS5 is working: look for `posts_fts` table in database
3. Try a simpler search term (FTS5 prefix mode may not match)

### Newsletter not sending

1. Verify SMTP credentials (`SMTP_USER`, `SMTP_PASSWORD` env vars)
2. Check `config.toml` `[email]` section has correct `smtp_host`, `smtp_port`
3. Look in `logs/blog.log` for `newsletter` or `smtp` errors
4. Ensure subscribers are **Confirmed** (not pending)

### Images not uploading

- Check `app/static/uploads/` exists and is writable
- Verify file size under 16 MB
- Ensure file type is allowed (JPEG, PNG, GIF, WebP, SVG)

### Database locked errors

- Usually means another process is writing
- With multiple workers, use `--workers 1` for newsletter to avoid conflicts
- Restart the server to clear stale connections

### High memory usage

- Reduce `workers` in Granian/Gunicorn
- Check `logs/blog.log` for memory leaks
- Run `flask cleanup-orphaned-images` to remove unused uploads

### Backup restore fails

- Ensure backup file is from the same version
- Check backup integrity: `flask check-integrity`
- Restore to empty database first, then import data

### CSS changes not applying

- Hard refresh: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
- Clear browser cache
- Check Custom CSS is enabled in `/admin/settings`
- Verify CSS syntax (look for red text in Custom CSS editor)

### Admin session expired

- Sessions last 24 hours by default (`SESSION_LIFETIME_HOURS` in `config.toml`)
- Check server time is correct
- Verify `PROXY_COUNT` is set correctly if behind reverse proxy

### Rate limiting causing 429 errors

Rate limiting is configured at the reverse proxy, not the app. Check your nginx/Caddy config. See [DEPLOY.md](DEPLOY.md#6-rate-limiting) for recommended limits.

---

## FAQ

### How do I change the site title/description?

Edit `config.toml`:
```toml
[app]
title = "My Blog"
description = "A blog about things"
```

### Can I use PostgreSQL instead of SQLite?

Yes. See the [PostgreSQL Migration Guide](DEPLOY.md#h4-postgresql-migration-guide) in DEPLOY.md.

### How do I enable HTTPS?

Configure a reverse proxy (nginx, Caddy) with SSL in front of the app. The app sets `SESSION_COOKIE_SECURE=True` automatically when `debug=False`.

### How do I export my data?

```bash
flask export-data backup.json
```

This exports posts, subscribers, and tags as JSON.

### How do I import data?

```bash
flask import-data backup.json
```

### How do I reset my admin password?

```bash
flask create-admin admin
```

Or use the password reset flow at `/admin/forgot-password`.

### How do I add multiple admins?

```bash
flask create-admin <username>
```

Then promote via `/admin/users` or `POST /admin/users/<id>/promote`.

### Can I disable newsletter?

Yes. Remove or comment out `[newsletter]` section in `config.toml`, or set `send_time=""`.

### How do I customize the footer?

Edit `config.toml`:
```toml
[site]
footer_html = "© 2026 My Blog"
```

### How do I get an API key?

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Set as `API_KEY` environment variable. Use as `X-API-Key` header.

### Where are the logs?

- Development: output to stdout
- Production: `logs/blog.log` (rotated at 10 MB, 10 backups)

### How do I rebuild the search index?

```bash
flask rebuild-search
```

### How do I clean up unused images?

```bash
flask cleanup-orphaned-images
```

### Why am I getting CSRF errors?

- Try clearing browser cookies
- Check that `CSRF_ENABLED` is not set to `false`
- Session may have expired—log out and back in

---

## Full Documentation

- [DEPLOY.md](DEPLOY.md) — Production deployment, PostgreSQL migration, Docker, systemd, monitoring
- [USAGE.md](USAGE.md) — Detailed user guide for all admin features
- [AGENTS.md](AGENTS.md) — Developer/contributor guidelines
