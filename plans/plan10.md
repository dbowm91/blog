# Documentation Improvement Plan (Plan 10)

**Date**: 2026-04-28  
**Goal**: Transform documentation from feature lists to actionable how-to guides

---

## Executive Summary

**Current State**: README.md lists features without explaining how to use them. 32+ implemented features are completely undocumented. Configuration options are incomplete (14 missing). The codebase is feature-rich but documentation doesn't reflect this.

**Goal**: Transform documentation from "feature lists" to "actionable how-to guides" while preserving the excellent technical reference in AGENTS.md.

---

## Research Findings Summary

### Subagent Investigations Completed:
1. **Public-facing features** (static pages, archive, search, sharing, preview links, short URLs, SEO)
2. **Admin features** (dashboard, analytics, revisions, bulk ops, media, sessions, users)
3. **Technical features** (API, CLI, config options, security headers, CSP nonces)
4. **Documentation best practices** (web research on Flask blog projects)

### Key Statistics:
- **32+ features** completely undocumented in README.md
- **14 configuration options** missing from documentation
- **15+ routes** missing from routes table
- **0 how-to sections** exist in current README

---

## 1. README.md Restructuring

### Current Issues (Lines 1-302)
- **Lines 5-12**: Feature list with no usage context
- **Lines 210-239**: Incomplete routes table (missing 15+ routes)
- **Lines 255-292**: Configuration incomplete (14 options missing)
- **No how-to sections**: Users can't learn how to use features

### Proposed New Structure

**Note:** Keep existing lines 21-38 from current README.md (Quick Start section), but add the two bullet points below to that section.

**Note:** The `markdown block below shows the NEW content structure for README.md.

```markdown
# DevLog

A personal blog platform built with Flask, featuring admin dashboard, newsletter, RSS feed, and analytics.

## Quick Start (3 Steps)
[Keep existing lines 21-38 from current README.md]

After setup:
- Visit `/admin/` to create your first post
- Public site at `/`, admin at `/admin/login`

## How to Use DevLog

### For Readers
**Searching Posts**
- Visit `/search?q=Flask+tutorial` for full-text search
- FTS5 with "Did you mean?" suggestions for typos
- Results show snippets with <mark> highlighting

**Subscribing to Newsletter**
- Enter email in footer → confirm via email link
- Double opt-in with constant-time token validation
- Unsubscribe via link in any newsletter

**Navigating the Blog**
- Homepage: Paginated posts with reading time estimates
- `/archive`: Chronological archive grouped by year/month
- `/tag/<slug>`: Filter posts by tag
- `/page/<slug>`: Static pages (About, Contact, etc.)
- Short URLs: `/s/<code>` redirects to full post URL

### For Admins
**Creating Posts**
1. Navigate to `/admin/` and click "New Post"
2. Write in Markdown (fenced code blocks, tables supported)
3. Upload images (magic byte validation, not extension-based)
4. Add tags with autocomplete
5. Set summary for SEO (or auto-truncate from body)
6. Publish immediately or schedule via `scheduled_publish_at`
7. Preview unpublished posts via shareable HMAC-signed links

**Managing Content**
- **Post Revisions**: Automatic history on each publish → `/admin/posts/<id>/revisions`
- **Bulk Operations**: Select multiple posts → publish/unpublish/delete/unschedule
- **Static Pages**: Create at `/admin/pages` → access at `/page/<slug>`
- **Media Library**: Upload/manage images at `/admin/media` (search, cleanup orphans)

**Configuring Newsletter**
1. Set SMTP credentials in `.env`: `SMTP_USER`, `SMTP_PASSWORD`
2. Configure in `config.toml`:
   ```toml
   [newsletter]
   send_time = "08:00"              # Daily send time
   confirmation_expiry_hours = 1      # Confirmation link expiry
   max_retry_attempts = 5             # Retry failed sends
   ```
3. Test via `/admin/newsletter-test`
4. Scheduler runs automatically (checks every 5 minutes)

**Viewing Analytics**
- Dashboard (`/admin/`): Total views, posts, shares, subscribers
- Trending posts (last 30 days), top shares, daily views chart
- Detailed analytics (`/admin/analytics`): Referrer categorization (Search/Social/Direct)

**Managing Admins**
- Create: `flask create-admin <username>` or via `/admin/users`
- Promote/demote: `/admin/users/<id>/promote` or `/admin/users/<id>/demote`
- Transfer ownership: `/admin/users/<id>/make-owner`
- Active sessions: `/admin/sessions` (revoke, IP binding warnings)

**Customizing Appearance**
- Themes: 4 presets (GitHub Dark/Light, Solarized Dark, Monokai) at `/admin/settings`
- Custom CSS: Enable + add rules (sanitized to block `url()`, `expression()`, etc.)
- Logo text: Set custom text (max 100 chars) or use site title

### Keyboard Shortcuts (Admin)
- `Ctrl+S`: Save draft
- `Ctrl+Enter`: Publish post
- `Ctrl+Shift+P`: Toggle preview
- `g` then `d`: Dashboard
- `g` then `s`: Subscribers
- `g` then `t`: Tags
- `?`: Show help

## Features (With Context)

### Content Management
- **Markdown Posts** — Live preview, image uploads (magic byte validation), SEO slugs, scheduled publishing
- **Static Pages** — About, Contact, etc. at `/page/<slug>` with Markdown support
- **Post Revisions** — Auto-save on publish, restore any version from history
- **Related Posts** — Auto-display posts sharing tags (configurable count, max 20)

### Discovery & Search
- **Full-Text Search** — SQLite FTS5 with LIKE fallback, "Did you mean?" suggestions, highlighted snippets
- **Archive** — Chronological (`/archive`) with cursor-based pagination (200/page)
- **Tag Filtering** — Browse by tag at `/tag/<slug>` with cached post counts
- **RSS & Sitemap** — RSS 2.0 feed at `/rss`, XML sitemap at `/sitemap.xml`
- **AI Blocker** — Robots.txt blocks GPTBot, Claude-Web, ChatGPT-User

### User Engagement
- **Social Sharing** — Track Twitter, Facebook, LinkedIn, Reddit, HackerNews shares
- **Short URLs** — Base62-encoded at `/s/<code>` (logs "link" share event)
- **Public Preview** — HMAC-signed links for unpublished posts (expires in 7 days)
- **Reading Time** — Auto-estimate (200 wpm, min 1 min) displayed on post cards
- **UI Features** — Image lightbox (keyboard nav), TOC (auto-generated), reading progress bar

### Admin Dashboard
- **Analytics** — Page views, shares, referrer categorization, daily views chart
- **Multi-Admin** — Create/promote/demote admins, transfer ownership
- **Session Management** — View active sessions, revoke access, IP binding warnings
- **Bulk Operations** — Publish/unpublish/delete multiple posts at once
- **Media Library** — Paginated gallery (50/page), search, orphan cleanup

### Newsletter
- **Double Opt-In** — Email confirmation with token (constant-time delay prevents enumeration)
- **Daily Digest** — APScheduler with file locking (`fcntl`) for single-machine deployments
- **Retry Logic** — Per-subscriber (3 attempts) + post-level (5 attempts)

### Security
- **CSRF Protection** — Sliding window of 5 valid tokens with timing-safe comparison
- **Password Security** — Werkzeug hashing (pbkdf2:sha256), complexity requirements (8+ chars, 3 of 4 classes)
- **Session Security** — Fixation prevention, configurable timeout (24h default)
- **Content Sanitization** — HTML (nh3), CSS injection prevention, CSV formula protection
- **Security Headers** — Comprehensive CSP with nonces, HSTS, X-Frame-Options

## Configuration

### Environment Variables (.env)
| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `SECRET_KEY` | Yes | Session signing key (min 32 chars) | Generated by setup.sh |
| `ADMIN_PASSWORD` | Yes | Admin login password | Generated by setup.sh |
| `ADMIN_USERNAME` | No | Admin username | `admin` |
| `API_KEY` | No | Enable REST API | (none) |
| `SMTP_USER` | No | SMTP username | (none) |
| `SMTP_PASSWORD` | No | SMTP password | (none) |
| `SESSION_COOKIE_SECURE` | No | HTTPS-only cookies | `true` |
| `PROXY_COUNT` | No | Reverse proxies in front | `1` |
| `HEALTH_CHECK_SECRET` | No | Secret for detailed `/health?details=` | (none) |

### Site Settings (config.toml)
```toml
[app]
title = "DevLog"
description = "Your blog description"
posts_per_page = 10              # Homepage pagination
session_lifetime_hours = 24      # Admin session timeout
max_viewed_posts = 100           # Cap session-stored viewed posts
tag_cache_ttl_seconds = 60        # Tag count cache TTL
dashboard_per_page = 20           # Admin dashboard pagination
subscribers_per_page = 50          # Subscriber list pagination
media_per_page = 50                # Media library pagination
media_max_files = 1000             # Max files shown in media
max_upload_size = 10485760         # Max upload size (10MB)
export_batch_size = 500             # CSV export batch size
fts_result_limit = 100              # Maximum search results
token_enumeration_delay = 0.1       # Constant-time delay (seconds)

[author]
name = "Your Name"
role = "Your Role"

[site]
base_url = "https://blog.example.com"  # No trailing slash
related_posts_count = 3               # Related posts shown (max 20)

[server]
host = "0.0.0.0"
port = 5000
debug = false                     # MUST be false in production

[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = ""                    # Override with SMTP_USER env var
smtp_password = ""                # Override with SMTP_PASSWORD env var
from_address = "blog@example.com"
smtp_timeout = 30                 # SMTP connection timeout (seconds)

[newsletter]
send_time = "08:00"               # Daily send time (HH:MM)
confirmation_expiry_hours = 1      # Confirmation link expiry
max_retry_attempts = 5            # Max retry attempts per post

[database]
url = ""                          # PostgreSQL URL (optional, SQLite default)
```

## REST API
**Authentication:** `X-API-Key: <your-key>` header (set `API_KEY` env var).

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts (pagination, filter by published) |
| POST | `/api/posts` | Create post |
| GET | `/api/posts/<id>` | Get single post |
| PUT | `/api/posts/<id>` | Update post |
| DELETE | `/api/posts/<id>` | Delete post |
| GET | `/api/subscribers` | List subscribers |
| POST | `/api/subscribers` | Create subscriber |
| DELETE | `/api/subscribers/<id>` | Delete subscriber |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/track-share` | Track share (no auth) |

**Full API Documentation:** `docs/openapi.yaml` (OpenAPI 3.0.3 spec)

**Example:**
```bash
# List published posts
curl -H "X-API-Key: $API_KEY" http://localhost:5000/api/posts?published=true

# Create a post
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"title": "Hello World", "body": "My first post", "published": true}' \
  http://localhost:5000/api/posts
```

## CLI Commands
Available via `flask <command>` (requires `ADMIN_PASSWORD` and `SECRET_KEY`):

| Command | Description | Example |
|---------|-------------|---------|
| `flask create-admin <user>` | Create/promote admin (interactive) | `flask create-admin alice` |
| `flask promote-admin <user>` | Promote existing user (non-interactive) | `flask promote-admin bob` |
| `flask check-integrity` | Run SQLite integrity check | `flask check-integrity` |
| `flask rebuild-search` | Rebuild FTS5 search index | `flask rebuild-search` |
| `flask cleanup-orphaned-images` | Delete unused uploaded images | `flask cleanup-orphaned-images` |
| `flask export-data <file>` | Export to JSON | `flask export-data backup.json` |
| `flask import-data <file>` | Import from JSON | `flask import-data backup.json` |
| `flask seed --posts N --subscribers M` | Generate test data | `flask seed --posts 50 --subscribers 100` |

**Seed options:** `--published` (publish all), `--draft` (keep drafts)

## Routes

### Public Routes
| Route | Description |
|-------|-------------|
| `GET /` | Homepage with paginated posts |
| `GET /post/<slug>` | Individual post (related posts, TOC, share buttons) |
| `GET /page/<slug>` | Static page |
| `GET /tag/<slug>` | Posts by tag |
| `GET /archive` | Chronological archive (year/month groups) |
| `GET /search?q=<query>` | Full-text search with snippets |
| `GET /s/<code>` | Short URL redirect (logs share event) |
| `GET /preview/<post_id>?token=<sig>&expires=<ts>` | Public preview (HMAC-signed) |
| `GET /rss` | RSS 2.0 feed |
| `GET /sitemap.xml` | XML sitemap |
| `GET /robots.txt` | Robots.txt (blocks AI crawlers) |
| `GET /health?details=<secret>` | Health check endpoint |
| `POST /subscribe` | Newsletter subscription |
| `GET /confirm/<token>` | Confirm subscription |
| `GET /unsubscribe/<token>` | Unsubscribe |

### Admin Routes
| Route | Description |
|-------|-------------|
| `GET /admin/login` | Login page |
| `POST /admin/login` | Authenticate |
| `GET /admin/` | Dashboard with analytics |
| `GET /admin/analytics` | Detailed analytics |
| `GET /admin/new` | New post form |
| `POST /admin/new` | Create post |
| `GET /admin/edit/<id>` | Edit post form |
| `POST /admin/edit/<id>` | Update post |
| `POST /admin/delete/<id>` | Delete post |
| `POST /admin/bulk-action` | Bulk publish/unpublish/delete |
| `GET /admin/posts/<id>/revisions` | Post revision history |
| `GET /admin/pages` | Static pages management |
| `GET /admin/media` | Media library |
| `GET /admin/subscribers` | Subscriber management |
| `GET /admin/tags` | Tag management |
| `GET /admin/users` | User management |
| `GET /admin/sessions` | Admin session management |
| `GET /admin/backup` | Backup/restore |
| `GET /admin/settings` | Theme and logo settings |
| `GET /admin/newsletter/test` | Test newsletter |
| `GET /admin/logout` | Logout |

## Installation

[Keep existing lines 19-65 from current README.md]

After setup:
- First user is auto-created on startup using `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- SQLite database created in `instance/blog.db`

### Docker (Optional)
```bash
docker build -t devlog .
docker run -p 5000:5000 --env-file .env devlog
```

## Deployment
### Production (Granian - Recommended)
```bash
pip install granian
granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 run:asgi_app
```
Full deployment guide: [DEPLOY.md](DEPLOY.md)

### Alternative: Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 --timeout 60 run:app
```

## Testing
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python -m pytest tests/ -v
# Without E2E: add --ignore=tests/e2e
```

## Project Structure

[Keep existing lines 162-208 from current README.md]

## Contributing
1. Fork the repo
2. Create a feature branch
3. Run tests: `pytest tests/ -v`
4. Submit PR

*Developer guidelines: [AGENTS.md](AGENTS.md)*

## License
Private – All rights reserved
```

---

## 2. Code References for Documentation

### Features to Document (With File Paths)

| Feature | File Path | Line Numbers | Current Doc State |
|---------|-----------|-------------|------------------|
| Static Pages | `app/routes/public.py` | 222-235 | Not in README |
| | `app/routes/admin/pages.py` | Full file | Not in README |
| Archive | `app/routes/public.py` | 120-219 | Missing from routes table |
| Search snippets | `app/search.py` | 222-261 | Listed but no usage |
| "Did you mean?" | `app/search.py` | 264-290 | Listed but no context |
| Share Tracking | `app/routes/api.py` | 469-510 | Not in README |
| | `app/models.py` (ShareEvent) | 215-230 | Not in README |
| Short URLs | `app/base62.py` | Full file | Not in README |
| | `app/routes/public.py` | 388-408 | Not in README |
| Preview Links | `app/routes/public.py` | 411-463 | Not in README |
| SEO (OG/Twitter/Schema) | `app/templates/base.html` | 8-21 | Not in README |
| | `app/templates/post.html` | 8-35 | Not in README |
| Related Posts | `app/routes/public.py` | 73-94 | Not in README |
| Reading Time | `app/__init__.py` | 191-197 | Not in README |
| Lightbox | `app/static/js/public/lightbox.js` | Full file | Not in README |
| TOC | `app/static/js/public/toc.js` | Full file | Not in README |
| Post Revisions | `app/routes/admin/posts.py` | 655-745 | Not in README |
| | `app/models.py` (PostRevision) | 149-167 | Not in README |
| Bulk Operations | `app/routes/admin/posts.py` | 506-624 | Listed but no usage |
| Media Library | `app/routes/admin/media.py` | Full file | Not in README |
| Admin Sessions | `app/routes/admin/sessions.py` | Full file | Not in README |
| | `app/models.py` (AdminSession) | 233-249 | Not in README |
| Multi-Admin | `app/routes/admin/users.py` | Full file | Listed but no details |
| Password Reset | `app/routes/admin/auth.py` | 117-216 | Not in README |
| Newsletter Retry | `app/email.py` | 99-134 | Not in README |
| | `app/scheduler.py` | 144-151 | Not in README |
| Backup/Restore | `app/routes/admin/backup.py` | Full file | Not in README |
| Theme Presets | `app/models.py` (THEME_PRESETS) | 275-365 | Listed but no details |
| CSS Sanitization | `app/utils.py` | 90-129 | Listed but no details |
| Keyboard Shortcuts | `app/static/js/admin/shortcuts.js` | Full file | Not in README |
| Health Check | `app/routes/public.py` | 828-914 | Missing from routes table |
| Structured Logging | `app/__init__.py` | 35-103 | Not in README |
| CSP Nonces | `app/__init__.py` | 229-230, 272-315 | Listed but no context |

---

## 3. AGENTS.md Updates (Minor)

### Add to top of file after line 3:
```markdown
**Note:** This file documents technical patterns and gotchas for developers/agents.
For user-facing documentation with how-to guides, see **README.md**.
For deployment, see **DEPLOY.md**.
```

### Add new section after "Project Structure":
```markdown
## Features Agents Should Know About

When working on these areas, see README.md for full documentation:

### Public Features
- **Static Pages**: `app/routes/admin/pages.py` (CRUD), `app/templates/page.html`
- **Archive**: Cursor-based pagination at `/archive` (200 posts/page)
- **Preview Links**: HMAC-signed tokens, 7-day expiry, works for drafts
- **Short URLs**: Base62 encoding, logs "link" share event
- **SEO**: Open Graph, Twitter Cards, schema.org Article in templates

### Admin Features  
- **Post Revisions**: Auto-saved on publish, restore at `/admin/posts/<id>/revisions`
- **Bulk Ops**: Uses `form="bulk-form"` attribute to avoid nested forms
- **Media Library**: 30-second cache TTL, orphan cleanup via CLI
- **Sessions**: IP binding logs warning (doesn't invalidate)
- **Newsletter**: Two-level retry (3 per-sub, 5 per-post), file locking for single-machine

### Technical Details
- **Reading Time**: 200 wpm, `round()` (not ceil), min 1 min
- **Related Posts**: Shared tags, configurable (default 3, max 20)
- **Search**: FTS5 with 300s availability cache, 100 result limit
- **Health Check**: Basic (`/health`), detailed (`?details=<secret>`)
- **Password Reset**: 1-hour expiry (HARDCODED, not configurable)
```

---

## 4. Critical Findings from Code

### Hardcoded Values (Not Configurable via config.toml)
1. **Password reset token expiry**: 1 hour (hardcoded in `app/routes/admin/auth.py:142`)
2. **Dashboard cache TTL**: 120 seconds (hardcoded in `app/routes/admin/helpers/dashboard.py:13`)
3. **Media cache TTL**: 30 seconds (hardcoded in `app/routes/admin/media.py:26`)
4. **Related posts hard limit**: 20 (hardcoded in `app/routes/public.py:59`)

### Security Notes
1. **Session IP binding**: Logs warning only (doesn't invalidate session)
2. **CSS sanitization**: 9 categories blocked (url, expression, content, behavior, mso-*, @import, -webkit-text-security, unicode-bidi, direction)
3. **CSRF token rotation**: On promote/demote/make-owner via `session.clear()`

### Two-Level Retry System (Newsletter)
1. **Per-subscriber**: 3 attempts (hardcoded in `app/email.py:104`)
2. **Post-level**: 5 attempts (configurable via `newsletter.max_retry_attempts`)

---

## 5. Implementation Checklist

- [ ] **README.md Lines 5-12**: Replace feature list with "How to Use" section
- [ ] **README.md Lines 210-239**: Expand routes table (add 15+ missing routes)
- [ ] **README.md Lines 255-292**: Expand configuration (add 14 missing options)
- [ ] **README.md**: Add "How to Use" subsections for readers and admins
- [ ] **README.md**: Add REST API section with examples
- [ ] **README.md**: Add CLI Commands section with table
- [ ] **README.md**: Add SEO features explanation
- [ ] **README.md**: Add keyboard shortcuts list
- [ ] **README.md**: Add Configuration section with all 20+ options
- [ ] **AGENTS.md**: Add note at top about purpose
- [ ] **AGENTS.md**: Add "Features Agents Should Know About" section
- [ ] **Verify**: All 32+ undocumented features now documented
- [ ] **Verify**: All configuration options explained with defaults
- [ ] **Verify**: CLI commands have examples
- [ ] **Verify**: API section links to `docs/openapi.yaml`
- [ ] **Verify**: Routes table complete (public + admin)

---

## 6. Documentation Best Practices Applied

### From Web Research:
1. **Actionable Documentation**: Show examples before explaining (curl commands first)
2. **Diátaxis Framework**: Tutorials/How-To/Explanation/Reference separation
3. **Two-Tier Config**: `.env` for secrets, `config.toml` for site settings
4. **Tables for Reference**: Configuration options, CLI commands, routes

### Structure Based on Examples:
- **DogukanUrker/FlaskBlog**: Quick start, features with context, Makefile commands
- **Flask-Blogging Docs**: Full ReadTheDocs hosting, configuration reference
- **Diátaxis Framework**: Industry standard for documentation structure

---

## 7. Files to Modify

| File | Changes Needed | Priority |
|------|----------------|----------|
| `README.md` | Complete restructure with how-to sections | High |
| `AGENTS.md` | Add note at top, add "Features Agents Should Know About" | Low |

### Files NOT to Modify:
- `DEPLOY.md` — Already comprehensive (keep as-is)
- `docs/openapi.yaml` — Already complete (keep as-is)

---

## 8. Success Criteria

After implementation:
1. README.md has 0 feature-only lists (all have usage context)
2. All 32+ undocumented features documented with file references
3. All 20+ configuration options documented with defaults
4. Routes table complete (30+ routes for public + admin)
5. CLI commands section with examples
6. API section with curl examples linking to OpenAPI spec
7. How-to sections for: creating posts, configuring newsletter, customizing theme
8. AGENTS.md updated with cross-references to README.md
