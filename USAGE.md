# User Guide

Detailed documentation for blog administration and content management.

## Contents

- [Post Writing Guide](#post-writing-guide)
- [Tags](#tags)
- [Post Series Guide](#post-series-guide)
- [Preview Links](#preview-links)
- [Syntax Highlighting](#syntax-highlighting)
- [Feeds (RSS and JSON)](#feeds-rss-and-json)
- [Newsletter Management](#newsletter-management)
- [Admin Tasks](#admin-tasks)
- [Analytics](#analytics)
- [User Management](#user-management)
- [Media Library](#media-library)
- [S3 Storage](#s3-storage)
- [Page View Buffer](#page-view-buffer)
- [Search](#search)
- [Short URLs](#short-urls)

---

## Post Writing Guide

### Creating a New Post

1. Navigate to `/admin/` (Dashboard)
2. Click **+ New Post** button
3. Fill in the post fields:

| Field | Description |
|-------|-------------|
| Title | Post title (shown in browser tab, social shares) |
| Body | Markdown content (see Markdown Tips below) |
| Tags | Comma-separated tag names |
| Summary | Optional excerpt, up to 500 characters. When empty, listings fall back to the start of the body |
| Image | Featured image (uploaded with a file picker) |
| Author | Post author, when more than one author exists |
| Publish immediately | Checkbox. Leave unchecked to keep the post as a draft |
| Schedule publication | Optional date/time. Publishes automatically once that time passes |

4. Click **Create Post** to save. Leave **Publish immediately** unchecked for a draft.

Authors (non-admin accounts) can only create and edit their own drafts;
publishing and scheduling are administrator decisions.

### Markdown Tips

**Headers for Table of Contents:**
```markdown
## Main Section      → H2 heading (appears in TOC)
### Subsection        → H3 heading (appears in TOC)
#### Sub-subsection   → H4 heading (not in TOC)
```

The table of contents is built from the `h2` and `h3` headings of the post
body and only appears when the post has at least three of them.

**Excerpt:**
The **Summary** field holds the excerpt used in listings, feeds and share
cards. There is no in-body divider — the excerpt is a separate field in the
editor, capped at 500 characters.

**Code Blocks:**
````markdown
```python
def hello():
    print("Hello, world!")
```
````

**Links and Images:**
```markdown
[Link text](https://example.com)
![Alt text](/static/uploads/image.png)
```

**Blockquotes:**
```markdown
> This is a blockquote.
```

### Previewing Posts

While editing, the live preview pane under the editor renders the post body
as you type. It can be collapsed with the **Hide Preview** / **Show Preview**
toggle. The preview:

- Renders Markdown to HTML
- Sanitizes HTML via nh3 (strips dangerous tags/attributes)
- Shows table of contents from h2/h3 headings
- Uses current theme styling

For a saved post, the **Preview** link opens the full post preview at
`/admin/preview/<post_id>` in a new tab.

### Editing Posts

1. Go to `/admin/`
2. Find your post and click **Edit**
3. Make changes
4. Click **Save Changes** to save changes

**Optional AI suggestions:** The post editor can use a local OpenAI-compatible server or OpenCode Go. The default local configuration is `http://127.0.0.1:1234/v1` with `google/gemma-4-e2b`; see `[ai]` in `config.toml.example`. A local server needs no API key. AI requests are unlimited by default; optionally set `ai.rate_limit_per_user` or `AI_RATE_LIMIT_PER_USER` using Flask-Limiter syntax. For compatible servers requiring authentication, set `AI_API_KEY` outside `config.toml`. To use OpenCode Go, set `provider = "opencode_go"`, choose a supported model, and supply `OPENCODE_GO_API_KEY` through the server environment or `.env`. AI actions send the current unsaved title and Markdown body only after an explicit click. Review suggestions before applying; nothing is saved until the normal post save. Local requests allow a longer response timeout, transient upstream failures are retried once, and a clear error appears if the configured server cannot be reached. See [AI authoring architecture](architecture/services/overview.md#optional-ai-authoring).

**Note:** If you see an "IntegrityError" message, a slug collision occurred. The system will auto-generate a new unique slug.

### Post Revisions

A revision is saved when a post is first published and again on every later
update to an already-published post:

1. While editing, click **Revisions** tab
2. View previous versions with author and timestamp
3. Click a revision to preview it
4. Click **Restore** to revert to that version

### Bulk Operations

From `/admin/`:

1. Check the box next to each post you want to modify
2. Select a bulk action from the dropdown:
   - **Publish** — Publish selected drafts
   - **Unpublish** — Take selected posts offline
   - **Unschedule** — Clear the scheduled publication time
   - **Delete** — Permanently remove (with confirmation)
3. Click **Apply**

### Scheduled Publishing

To schedule a post for future publication:

1. While creating/editing a post, find **Schedule publication** field
2. Select a future date and time
3. Click **Create Post** / **Save Changes** without checking **Publish immediately**

The scheduler checks every 5 minutes for posts with `scheduled_publish_at` in the past. When triggered, the post is automatically published and the scheduled time is cleared.

**Status indicators on `/admin/`:**
- Clock icon = Scheduled
- Green dot = Published
- Gray dot = Draft

### Short URLs

Each post gets a short URL: `/s/<code>` where `<code>` is a base62-encoded post ID.

- Find the short URL in the post edit page
- Useful for sharing on Twitter/character-limited platforms
- Short codes never change, even if the slug does

---

## Tags

Tags organize posts by topic and appear in the sidebar for filtering.

### Viewing Tags

Go to `/admin/tags` to see all tags with post counts.

### Creating Tags

1. Go to `/admin/tags`
2. Type the tag name in the **New tag name** field at the top of the page
3. The slug is generated from the name automatically
4. Click **Create**

### Editing Tags

1. Go to `/admin/tags`
2. Edit the name in the inline field next to the tag
3. Click **Rename** — the slug is regenerated from the new name

**Note:** Changing a tag's slug may break existing links to posts filtered by that tag.

### Deleting Tags

1. Go to `/admin/tags`
2. Click **Delete** next to the tag
3. Confirm deletion

**Warning:** Deleting a tag removes it from all posts. This cannot be undone.

### Tag Sidebar

The sidebar shows all tags with post counts. Click a tag to filter posts.

The footer tag column is controlled separately, from **Settings → Site**:
`footer_show_tags` toggles the "Browse by tag" column.

### Tag Cloud

Tags are displayed as a simple list sorted by name. No weighted tag cloud by default.

---

## Post Series Guide

Post series let you group related posts into ordered collections with sequential navigation.

### Workflow
1. Go to `/admin/series`
2. Click **+ New Series**
3. Enter:
   - **Series Name** — Display name (e.g., "Flask Tutorials")
   - **Slug** — URL-friendly version (auto-generated if empty)
   - **Description** — Optional summary
4. Click **Create Series**
5. Add posts to a series from the series page:
   - Go to `/admin/series/<id>/posts` (**Manage Posts** on the series list)
   - Pick a post in the **Add Posts to Series** select
   - Click **Add Post to Series**
   - Reorder entries from the same page if needed

### Example
Create a "Python Basics" series, add 3 posts in order: "Variables", "Loops", "Functions". The series page at `/series/python-basics` shows all posts in order with previous/next navigation.

### Comparison with Tags
| Feature | Tags | Post Series |
|---------|------|-------------|
| Organization | Unordered many-to-many | Ordered one-to-many (post belongs to 0-1 series) |
| Purpose | Filter posts by topic | Group sequential/related content |
| Display | Sidebar filter, post tags | Series badge on posts, dedicated series page |
| Navigation | None | Previous/next post links in series |

---

## Preview Links

Shareable preview links let you share unpublished posts with reviewers without publishing them.

### HMAC Security
Preview links use HMAC-SHA256 signed tokens to prevent unauthorized access:
- Token includes post ID and expiry timestamp
- Signed with `SECRET_KEY` to prevent tampering
- Tokens are validated on every access

### Expiry
Tokens expire after 7 days by default. Configure the expiry in `config.toml`:

```toml
[app]
preview_token_expiry_days = 7
```

The equivalent environment variable is `PREVIEW_TOKEN_EXPIRY_DAYS`.

### Programmatic Generation
Generate preview links via the admin API or code:
1. **Admin endpoint**: `GET /admin/preview/<post_id>?share=1` returns the signed
   preview URL and its expiry timestamp as JSON
2. **Code**:
```python
import hmac
import hashlib
import time
import base64
from flask import current_app

def generate_preview_link(post_id):
    expires = int(time.time()) + (7 * 86400)  # 7 days
    message = f"{post_id}:{expires}"
    signature = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    token = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"/preview/{post_id}?token={token}&expires={expires}"
```

---

## Syntax Highlighting

The blog uses Prism.js for syntax highlighting of code blocks in posts.

There is no syntax highlighting theme setting. The Prism token colours are
mapped onto the site's own theme tokens, so a code block follows the theme it
is read in. Prism itself is bundled from the npm package and is only fetched
when a page actually contains a code block.

---

## Feeds (RSS and JSON)

The blog provides RSS and JSON feeds for subscribers and feed readers.

### RSS Feed

**URL:** `/rss`

RSS 2.0 compliant feed with:
- Post title, link, description (summary or body excerpt)
- Publication date
- Category tags
- Author name

The feed contains the 20 most recent published posts. There is no `?limit=`
parameter; the item count is fixed.

**Usage:**
```xml
<!-- Example RSS feed item -->
<item>
  <title>My Blog Post</title>
  <link>https://blog.example.com/post/my-blog-post</link>
  <description>Summary of the post...</description>
  <pubDate>Wed, 29 Apr 2026 12:00:00 GMT</pubDate>
  <guid isPermaLink="true">/s/abc123</guid>
</item>
```

### Atom Feed

**URL:** `/atom`

Atom 1.0 feed with the same content as the RSS feed.

### JSON Feed

**URL:** `/json`

JSON Feed 1.1 compliant feed with:
- Title, description, URL
- Post items with `content_html` (full rendered content)
- Author information
- Tags as categories

The feed contains the 20 most recent published posts. There is no `?limit=`
parameter; the item count is fixed.

**Usage:**
```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "DevLog",
  "items": [
    {
      "id": "/s/abc123",
      "url": "/post/my-blog-post",
      "title": "My Blog Post",
      "content_html": "<p>Full rendered content...</p>",
      "date_published": "2026-04-29T12:00:00Z",
      "tags": ["python", "flask"]
    }
  ]
}
```

### Feed Discovery

The built-in base template already publishes the Atom feed link. To offer the
other formats as well, add these to your `<head>`:

```html
<link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/rss">
<link rel="alternate" type="application/atom+xml" title="Atom Feed" href="/atom">
<link rel="alternate" type="application/json" title="JSON Feed" href="/json">
```

Per-tag and per-series feeds are also available:
`/tag/<slug>/rss`, `/tag/<slug>/atom`, `/tag/<slug>/json` and the matching
`/series/<slug>/…` paths.

### Conditional GET (ETag Support)

Both feeds support conditional GET:
- Request with `If-None-Match` header
- Returns `304 Not Modified` if feed hasn't changed
- Reduces bandwidth for frequent feed readers

### Cache-Control Headers

Feeds include cache headers to control caching:
- `Cache-Control: public, max-age=3600` (1 hour)
- Varies on `Accept-Encoding` for compression

### Feed Validation

Validate your feeds at:
- RSS: https://validator.w3.org/feed/
- JSON: https://jsonfeed.org/validator/

---

## Newsletter Management

### How Newsletter Works

1. You publish a post with `newsletter_sent_at = NULL`
2. The scheduler picks it up at the configured send time
3. Emails go to all **confirmed** subscribers
4. Each subscriber gets an email with:
   - Post title and summary
   - Link to full post
   - One-click unsubscribe link

When the send succeeds, `newsletter_sent_at` is stamped on each post so it is
not sent again. When it fails, `newsletter_attempts` is incremented and the
post is retried on the next run, up to `max_retry_attempts` times.

The daily newsletter job is only scheduled when `SMTP_HOST` is configured.
The other scheduled jobs (scheduled publishing, subscriber cleanup, daily
backup) run regardless.

### Configuring Newsletter

Edit `config.toml`:

```toml
[newsletter]
send_time = "08:00"              # HH:MM (24h) - time to send the daily digest
confirmation_expiry_hours = 1    # Hours until a confirmation link expires
max_retry_attempts = 5           # Retry attempts on failure
```

Edit SMTP settings:

```toml
[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "your-email@gmail.com"
smtp_password = "your-app-password"  # Use App Password for Gmail
from_address = "blog@example.com"
smtp_timeout = 30
```

Or set via environment variables: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`.

### Sending a Newsletter

The daily digest is sent automatically by the scheduler — there is no manual
"send to all subscribers" button. From the dashboard you can:

- **Preview Newsletter** — renders the newsletter email with the 3 most recent
  published posts, without sending anything
- **Test Newsletter** — sends the same 3 posts to an address you choose
  (defaults to the configured `from_address`)

To include a specific post in the next digest, publish it and leave
`newsletter_sent_at` empty. The dashboard shows a **Reset NL** button on posts
that were already sent, which clears the flag so they go out again.

Progress is logged to `logs/blog.log`.

### Subscriber Confirmation Flow

1. Visitor subscribes at `/subscribe`
2. Receives confirmation email with link
3. Clicks link → `/confirm/<token>`
4. Email marked as **Confirmed**

Unconfirmed subscribers don't receive newsletters.

### Resending Confirmation Emails

1. Go to `/admin/subscribers`
2. Select unconfirmed subscribers
3. Choose **Resend Confirmation** from bulk actions
4. Click **Apply**

### Unsubscribe Flow

Every newsletter email includes an unsubscribe link of the form:
```
{base_url}/unsubscribe/<subscriber-token>
```

Clicking the link:
- Marks subscriber as unsubscribed
- Shows success message (same message for valid/invalid tokens—prevents enumeration)

### Newsletter Templates

The newsletter email template is in `app/templates/email/newsletter.html`. Customize by editing this file.

---

## Admin Tasks

### Dashboard

The dashboard at `/admin/` shows:

- **Stat cards** — Total Views, Published Posts, Total Shares, Subscribers (and Scheduled & Ready when there are scheduled posts)
- **Traffic (30 days)** — Page views over the last 30 days
- **Top Shares (30 days)** — Most-shared posts over the last 30 days
- **Trending (30 days)** — Posts with the most views over the last 30 days
- **Recent Posts** — Latest published posts, with bulk actions
- **Newsletter actions** — Preview Newsletter, Test Newsletter, + New Post

### Backup and Restore

1. Go to `/admin/backup`
2. Click **Create Backup**
3. Optionally enable compression
4. Optionally enable encryption (requires `BACKUP_ENCRYPTION_KEY` env var)
5. Backups appear in the list below

**To restore:**
1. Find your backup in the list
2. Click **Restore**
3. Confirm the action

**Warning:** Restoring overwrites all current data.

**Backup location:** `<data_dir>/backups/` — the directory next to the
database (`/var/lib/devlog/backups` in system scope,
`~/.local/share/devlog/backups` in user scope, `./data/backups` in
development).

**Backup database path:** every backup path resolves the database from the
configured URI (`<data_dir>/devlog.sqlite3` by default) and writes to the
directory above — the admin **Create Backup** button, the APScheduler daily
backup and `devlog backup create` alike.

**Backup encryption:**
```bash
export BACKUP_ENCRYPTION_KEY="your-secure-passphrase"
```

Encrypted backups use AES-256-GCM encryption with PBKDF2 key derivation.

### Database Integrity Check

The backup page offers Create Backup, Download, Restore and Delete per
backup. Integrity checking is done from the CLI:

```bash
# Database integrity
flask check-integrity
devlog db check

# Verify one backup file
devlog backup verify data/backups/blog_20260429_030000.db
```

The same verification is reachable over HTTP at
`/admin/backup/verify-all` and `/admin/backup/verify/<filename>`.

### Static Pages

Create static pages (accessible at `/page/<slug>`):

1. Go to `/admin/pages`
2. Click **New Page**
3. Enter:
   - **Title** — Page title
   - **Slug** — URL slug (auto-generated if empty)
   - **Content** — Markdown content
4. Toggle **Published** as needed
5. Click **Create Page** (or **Save Changes** when editing)

Published pages are listed at `/pages`. Individual pages are served from
`/page/<slug>`; there are no fixed built-in page URLs.

### Settings

The admin settings live on one page, `/admin/settings`, split into sections:

| Section | Contents |
|---------|----------|
| Theme Preview | Live preview of the selected dark/light theme pair |
| Theme | Dark theme, light theme, default colour scheme, logo text, custom CSS |
| Theme Registry | The bundled theme catalogue, with warnings |
| Typography & Background | Sans and mono font families, and the page backdrop |
| Site | Comments toggle, footer text, footer columns, page menu |

| Setting | Description |
|---------|-------------|
| Dark theme / Light theme | Halloy theme names, chosen from the bundled catalogue of 50 |
| Default scheme | Which theme applies when the visitor has no saved colour-scheme preference (`system`, `dark` or `light`) |
| Logo Text | Text to display as logo (uses the site title if empty) |
| Custom CSS | Additional CSS (sanitized before saving) |
| Font (sans / mono) | Font families from the appearance registry |
| Backdrop | Page backdrop from the appearance registry |
| Comments | Enables or disables the comment form |
| Footer Text | Plain-text footer line (HTML is not accepted) |
| Footer columns | Show the posts column, the tags column, or both |
| Page menu | Which published pages appear in the navigation bar |

Each section posts to its own endpoint: `/admin/settings/theme`,
`/admin/settings/appearance` and `/admin/settings/site`.

**CSS Custom Properties:**
```css
:root {
    --bg: #0d1117;
    --bg-surface: #161b22;
    --text: #c9d1d9;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --border: #30363d;
}
```

### API Key Management

The REST API uses API key authentication. Set via environment variable:
```bash
export API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

Send it as an `X-API-Key` header. The legacy `API_KEY` environment variable
grants every scope. Scoped tokens (`ApiToken` records) carry an explicit scope
list:

| Category | Scopes |
|----------|---------|
| posts | `posts:read`, `posts:write`, `posts:*` |
| pages | `pages:read`, `pages:write`, `pages:*` |
| series | `series:read`, `series:write`, `series:*` |
| tags | `tags:read`, `tags:write`, `tags:*` |
| media | `media:read`, `media:write`, `media:*` |
| subscribers | `subscribers:read`, `subscribers:write`, `subscribers:*` |
| newsletter | `newsletter:send`, `newsletter:*` |
| analytics | `analytics:read`, `analytics:*` |
| all | `admin:*` |

An exact scope grants that operation; a category wildcard grants every scope
in that category; `admin:*` grants everything. See `docs/openapi.yaml` for
the API documentation.

### CLI Commands

Flask CLI commands (compatibility wrappers over the same services):

```bash
# Export all data
flask export-data data.json

# Import data
flask import-data data.json

# Rebuild search index
flask rebuild-search

# Clean unused images
flask cleanup-orphaned-images

# Check database integrity
flask check-integrity

# Create admin user (prompts for the username and password)
flask create-admin

# Promote to admin
flask promote-admin username

# Generate sample data
flask seed

# Shell access
flask shell
```

The standalone `devlog` CLI covers the same ground with structured output and
extra operator tooling:

```bash
devlog admin create              # Create an admin account
devlog admin list                # List accounts
devlog data export data.json     # Export posts, subscribers, tags and pages
devlog data import data.json --apply  # Import them back (--dry-run to preview)
devlog db rebuild-search         # Rebuild the FTS index
devlog media cleanup --apply     # Remove orphaned uploads (no flag = report only)
devlog db check                  # Database integrity check
devlog backup verify <path>      # Verify a backup file
devlog doctor                    # Run the full diagnostic suite
devlog themes list --warnings    # Inspect the theme catalogue
devlog serve                     # Run the ASGI server in the foreground
devlog worker                    # Run the Celery worker in the foreground
devlog scheduler                 # Run the scheduler in the foreground
```

See [DEPLOY.md](DEPLOY.md#17-operator-cli) for the full command list.

---

## Analytics

### Page Views

The blog tracks page views for each published post.

**How it works:**
- When a post is viewed, `PageViewBuffer.record_page_view()` is called
- By default, views are recorded directly to the database
- For high-traffic sites, enable the **Page View Buffer** (see below)

**Viewing analytics:**
1. Go to `/admin/analytics`
2. See charts for:
   - Page views over time (last 30 days)
   - Top posts by views
   - Traffic sources (referrers)

**Manual view recording:**
```python
from app.page_view_buffer import record_page_view
record_page_view(post_id=1, referrer="https://twitter.com/")
```

### Share Events

When a visitor shares a post via the share buttons, a `ShareEvent` is recorded.

**Share platforms:**
- `twitter` — Twitter/X
- `facebook` — Facebook
- `linkedin` — LinkedIn
- `hackernews` — Hacker News
- `reddit` — Reddit
- `link` — Copy link (the **Copy** button) or the short `/s/<code>` URL

Only those six values are accepted by `/api/track-share`; anything else is
rejected with `400`.

**Viewing share data:**
Top shares appear on the dashboard at `/admin/`.

### Interpreting Analytics

#### Traffic Sources
Traffic sources are captured from the `referrer` header of page views:
- **Direct**: No referrer (user typed URL or used bookmark)
- **Search**: Google, Bing, Yahoo, DuckDuckGo
- **Social**: Twitter/X, Facebook, LinkedIn, Reddit
- **Other**: All other referrers

Use traffic sources to identify which channels drive the most engagement.

#### Share Events
- **Count**: Total shares per platform
- **Trend**: Compare week-over-week share counts
- **Top Shared Posts**: Appear on the dashboard, indicating popular content worth promoting

High share counts correlate with increased traffic from social channels.

### Analytics API

```bash
# Blog-wide counters (requires the analytics:read scope)
GET /api/stats

# Response fields: total_views, total_posts, total_shares,
# total_subscribers, views_this_month, new_subscribers_this_month
```

Post listings are paginated with `page` and `per_page` (default 20, maximum
100); the post payload does not include a view count.

```bash
GET /api/posts?page=1&per_page=20
```

---

## User Management

### User Roles

| Role | Description |
|------|-------------|
| Author | Signed-in, non-admin account. Reaches the post editor and their own profile only, and may only open their own posts. Cannot publish |
| Admin | Full access to the admin panel, including publishing, scheduling, users, settings and media |

There is no separate stored "owner" role. Ownership is expressed by the
**Transfer Owner** action, which promotes one account to admin and demotes
every other admin. Every admin can promote, demote and delete users.

### Creating Users

**Via CLI:**
```bash
flask create-admin
```
Prompts for the username and password.

The standalone CLI does the same with structured output:
```bash
devlog admin create
```

**Via Admin Panel:**
1. Go to `/admin/users`
2. Fill in the **Create User** form at the bottom of the page
3. Enter username and password, and tick the **Admin** box if needed
4. Click **Create**

### Password Requirements

- Minimum 8 characters
- At least 3 of: uppercase, lowercase, digits, special characters

### Promoting/Demoting Admins

1. Go to `/admin/users`
2. Find the user
3. Click **Promote** to make admin, or **Demote** to remove admin

**Note:** You cannot demote yourself if you're the only admin.

### Transferring Ownership

1. Go to `/admin/users`
2. Find the new owner
3. Click **Transfer Owner** and enter your own password to confirm

This demotes all other admins and promotes the selected user to admin.

### Password Reset

1. Go to `/admin/forgot-password`
2. Enter your username
3. Check email for reset link (valid 1 hour)
4. Click link → `/admin/reset/<token>`
5. Enter new password

**Security:** Invalid tokens show success (prevents enumeration). Tokens are hashed with SHA-256 before storage.

### Session Management

View active sessions at `/admin/sessions`:

- Shows username, IP address, user agent, last activity
- Current session highlighted
- Click **Revoke** to force logout

Sessions auto-expire after 24 hours of inactivity (configurable via `SESSION_LIFETIME_HOURS`).

**IP Binding:** If your IP changes, a warning is logged. The session isn't invalidated (allows for mobile users switching networks).

---

## Media Library

### Accessing Media Library

Go to `/admin/media`

### Uploading Images

1. Go to `/admin/media`
2. Drag & drop images onto the upload zone, or click it to browse
3. Wait for the upload to complete

**Limits:**
- Max file size: 10 MB
- Allowed types: image/jpeg, image/png, image/gif, image/webp

### Responsive Images

On upload, images are automatically resized to create variants:
- 400w, 800w, 1200w widths
- WebP and AVIF format when supported

Templates use `srcset` for responsive loading:
```html
<img src="/static/uploads/image.jpg"
     srcset="/static/uploads/400_image.jpg 400w,
             /static/uploads/800_image.jpg 800w,
             /static/uploads/1200_image.jpg 1200w"
     sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px">
```

### Using Images in Posts

1. Copy the image URL from the media library
2. In your post, use Markdown:
   ```markdown
   ![Alt text](/static/uploads/filename.png)
   ```

For the post's featured image, use the **Featured image** file picker in the
post editor instead.

### Deleting Images

1. Go to `/admin/media`
2. Click on the image
3. Click **Delete**
4. Confirm

**Warning:** Deleted images are permanently removed. If an image is in use by a post, the post will show a broken image.

### Image Storage

**Local storage (default):**
Images are stored in `app/static/uploads/`. This directory should be included in
backups. Override the location with the `UPLOAD_FOLDER` environment variable.

**S3 storage:**
Images are stored in S3-compatible storage. See [S3 Storage](#s3-storage) section.

### Cleaning unused images

```bash
flask cleanup-orphaned-images
```

This removes images not referenced by any post. The standalone CLI equivalent
is `devlog media cleanup --apply` — without `--apply` it only reports what
would be removed.

### How Image Uploads Work

1. File uploaded to storage
2. Magic bytes detected to verify file type
3. Extension set based on detected type (not user-provided)
4. Filename: `<random-uuid-hex>.<ext>`

---

## S3 Storage

The blog supports storing media files in S3-compatible storage instead of local filesystem.

### Prerequisites

S3 support requires `boto3`, which ships as the optional `s3` extra:

```bash
pip install ".[s3]"
```

### Configuration

Set environment variables:

```bash
export STORAGE_BACKEND=s3
export S3_BUCKET=my-blog-uploads
export S3_REGION=us-east-1
export S3_ACCESS_KEY=AKIA...
export S3_SECRET_KEY=...
```

**Optional:**
```bash
export S3_ENDPOINT=https://s3.amazonaws.com    # For S3-compatible services
export S3_PUBLIC_URL=https://cdn.example.com      # Custom CDN URL
```

### Supported S3-Compatible Services

- Amazon S3
- Cloudflare R2
- MinIO
- Wasabi
- Any S3-compatible API

### How S3 Storage Works

1. Image uploaded via admin panel
2. Saved to a temporary file locally
3. Responsive variants generated
4. All variants uploaded to S3
5. Local temporary files deleted

**Reading images:**
- The `post_image_url` filter uses `storage.url()` to generate URLs
- With `S3_PUBLIC_URL` set, URLs are built from that CDN base; otherwise the
  S3 virtual-hosted URL (`https://<bucket>.s3.<region>.amazonaws.com/<key>`)
  is used
- URLs are not signed — a private bucket needs a CDN or a public-read policy

### Storage Backend Detection

The app auto-detects storage backend from `STORAGE_BACKEND`:
- `local` (default) — Local filesystem
- `s3` — S3-compatible storage

### Local Storage Fallback

If `STORAGE_BACKEND=s3` but `S3_BUCKET`, `S3_ACCESS_KEY` or `S3_SECRET_KEY`
is missing, the app logs a warning at startup and falls back to local storage
at `app/static/uploads/`. This decision is made once, at startup — it is not a
runtime retry when S3 becomes unreachable.

### Migration from Local to S3

1. Configure S3 environment variables
2. Restart the app
3. New uploads go to S3
4. Existing local uploads remain in place — copy them across if you want them
   served from S3

---

## Page View Buffer

For high-traffic sites, page views can be buffered and batch-written to reduce database load.

### Enabling the Buffer

```bash
# Enable buffer (flush when buffer reaches 100 views)
export PAGE_VIEW_BUFFER_SIZE=100

# Flush interval in seconds (default: 5)
export PAGE_VIEW_FLUSH_INTERVAL=10
```

Set `PAGE_VIEW_BUFFER_SIZE=0` to disable buffering (default behavior).

The buffer size can also be set in `config.toml`:

```toml
[app]
page_view_buffer_size = 100
```

`PAGE_VIEW_FLUSH_INTERVAL` is an environment variable only; it has no
`config.toml` key.

### How It Works

1. Visitor views a post
2. `record_page_view()` adds to buffer (thread-safe)
3. Background thread flushes buffer when:
   - Buffer reaches `PAGE_VIEW_BUFFER_SIZE`, OR
   - `PAGE_VIEW_FLUSH_INTERVAL` seconds elapsed since last flush
4. All buffered views written in single batch insert

### Benefits

- Reduces database writes for high-traffic sites
- Thread-safe (works with multiple workers)
- Graceful shutdown (flushes remaining buffer)

### Monitoring

Check logs for buffer activity:
```
PageViewBuffer started (max_size=100, flush_interval=10s)
PageViewBuffer stopped (flushed=123, dropped=0)
```

### Manual Flush

```python
from app.page_view_buffer import shutdown_page_view_buffer
shutdown_page_view_buffer()  # Flushes and stops background thread
```

### Integration with Analytics

The analytics system (page views, share events) works identically with or without buffering. No code changes required.

---

## Search

### Using Search

1. Use the search bar in the header
2. Results show as you type (debounced)
3. Use arrow keys to navigate, Enter to select, Escape to close

### Search Features

- **Full-text search** via SQLite FTS5
- **Prefix matching** — searching "Py" matches "Python"
- **Did you mean?** — suggestions for typos
- **Highlighted matches** — search terms highlighted in results

### Rebuilding the Search Index

If search results seem wrong:

```bash
flask rebuild-search
```

This recreates the FTS5 table and reindexes all posts.

### Search API

```bash
# Full-text search page (HTML)
GET /search?q=search+term&page=1

# Live-search suggestions (JSON)
GET /search/suggest?q=search+term
```

`/search/suggest` returns up to five matching posts as
`{"suggestions": [{"title": ..., "slug": ..., "summary": ...}]}`.

### FTS5 Limitations

- FTS5 is SQLite-specific (PostgreSQL migration requires different search implementation)
- Prefix search limited to 2-4 character prefixes
- Very long documents may not be fully indexed

---

## Short URLs

Each post has a short URL at `/s/<code>` where `<code>` is a base62-encoded post ID.

**Examples:**
- Post ID 1 → `/s/1`
- Post ID 100 → `/s/1C`
- Post ID 1000 → `/s/g8`

**Benefits:**
- Never changes (even if slug changes)
- Short for sharing on Twitter
- Always works regardless of slug

Find the short URL in the post edit page.

**Encoding:**
```python
from app.base62 import encode
code = encode(post_id)  # e.g., 1000 -> "g8"
```

**Decoding:**
```python
from app.base62 import decode
post_id = decode(code)  # e.g., "g8" -> 1000
```
